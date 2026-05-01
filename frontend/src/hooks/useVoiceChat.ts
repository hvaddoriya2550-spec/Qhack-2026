import { useCallback, useRef, useState } from "react";
import { useChatStore } from "../store/chatStore";
import type { Message } from "../types/chat";

const VOICE_CHAT_URL = (import.meta.env.VITE_API_URL || "") + "/api/v1/voice/chat";

// Silence detection config
const SILENCE_THRESHOLD = 0.015; // RMS level below which we consider "silence"
const SILENCE_DURATION_MS = 1800; // How long silence must last to auto-stop

interface VoiceChatState {
  isRecording: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  isLoopActive: boolean;
  error: string | null;
}

interface VoiceChatResponse {
  transcript: string;
  reply: string;
  spoken_summary?: string;
  conversation_id: string;
  agent_name?: string;
  phase?: string;
  audio_base64?: string | null;
}

/** Currently playing audio element — stored so we can stop it */
let currentAudio: HTMLAudioElement | null = null;

/**
 * Play base64-encoded MP3 audio from ElevenLabs.
 */
function playAudioBase64(base64: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const audio = new Audio(`data:audio/mpeg;base64,${base64}`);
    currentAudio = audio;
    audio.onended = () => { currentAudio = null; resolve(); };
    audio.onerror = (e) => { currentAudio = null; reject(e); };
    audio.play().catch(reject);
  });
}

/**
 * Fallback: speak text using the browser's built-in SpeechSynthesis API.
 */
function speakTextBrowser(text: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (!("speechSynthesis" in window)) {
      reject(new Error("Speech synthesis not supported"));
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(
      (v) =>
        v.lang.startsWith("en") &&
        (v.name.includes("Google") ||
          v.name.includes("Natural") ||
          v.name.includes("Samantha") ||
          v.name.includes("Daniel")),
    );
    if (preferred) utterance.voice = preferred;

    utterance.onend = () => resolve();
    utterance.onerror = (e) => reject(e);

    window.speechSynthesis.speak(utterance);
  });
}

/** Play ElevenLabs audio if available, otherwise fall back to browser TTS. */
async function speak(text: string, audioBase64?: string | null): Promise<void> {
  if (audioBase64) {
    return playAudioBase64(audioBase64);
  }
  return speakTextBrowser(text);
}

/** Trim long responses for speech — keep it concise, full text stays in chat. */
function trimForSpeech(text: string, maxLen = 350): string {
  // Strip markdown formatting
  let clean = text
    .replace(/#{1,6}\s/g, "")
    .replace(/\*{1,3}([^*]+)\*{1,3}/g, "$1")
    .replace(/---+/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[`~]/g, "")
    .trim();

  if (clean.length <= maxLen) return clean;

  // Take the first paragraph or sentence block
  const firstPara = clean.split(/\n\n/)[0] || clean;
  if (firstPara.length <= maxLen) {
    return firstPara + ". Check the chat for full details.";
  }

  // Truncate at last sentence boundary within limit
  const truncated = clean.slice(0, maxLen);
  const lastPeriod = truncated.lastIndexOf(".");
  if (lastPeriod > 100) {
    return truncated.slice(0, lastPeriod + 1) + " Check the chat for full details.";
  }

  return truncated + "... Check the chat for full details.";
}

function stopAllAudio() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  window.speechSynthesis.cancel();
}

/**
 * Full voice mode: continuous conversation loop.
 * Record → auto-stop on silence → transcribe → agent → TTS → repeat.
 */
export function useVoiceChat(projectId?: string) {
  const store = useChatStore();
  const [state, setState] = useState<VoiceChatState>({
    isRecording: false,
    isProcessing: false,
    isSpeaking: false,
    isLoopActive: false,
    error: null,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const silenceTimerRef = useRef<number | null>(null);
  const silenceCheckRef = useRef<number | null>(null);
  const loopActiveRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);

  const cleanup = useCallback(() => {
    if (silenceCheckRef.current) {
      clearInterval(silenceCheckRef.current);
      silenceCheckRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    mediaRecorderRef.current = null;
    analyserRef.current = null;
  }, []);

  const startRecording = useCallback(async () => {
    setState((s) => ({ ...s, isRecording: true, error: null }));

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Set up audio analysis for silence detection
      const audioCtx = new AudioContext();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      analyserRef.current = analyser;

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        // Only process if we have meaningful audio (> 1KB)
        if (blob.size > 1000) {
          await processVoiceRoundTrip(blob);
        } else {
          // Too short, restart listening if loop is active
          if (loopActiveRef.current) {
            startRecording();
          }
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250); // collect chunks every 250ms

      // Start silence detection
      monitorSilence();
    } catch {
      setState((s) => ({
        ...s,
        isRecording: false,
        error: "Microphone access denied",
      }));
    }
  }, []);

  const monitorSilence = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const dataArray = new Float32Array(analyser.fftSize);
    let silenceStart: number | null = null;

    // Use setInterval instead of requestAnimationFrame so it
    // keeps running when the browser tab is in the background.
    const check = () => {
      if (!analyserRef.current || !mediaRecorderRef.current) return;
      if (mediaRecorderRef.current.state !== "recording") return;

      analyser.getFloatTimeDomainData(dataArray);

      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        const val = dataArray[i]!;
        sum += val * val;
      }
      const rms = Math.sqrt(sum / dataArray.length);

      if (rms < SILENCE_THRESHOLD) {
        if (!silenceStart) {
          silenceStart = Date.now();
        } else if (Date.now() - silenceStart > SILENCE_DURATION_MS) {
          stopRecording();
          return;
        }
      } else {
        silenceStart = null;
      }
    };

    // Wait before starting detection so we don't trigger on initial silence
    silenceTimerRef.current = window.setTimeout(() => {
      silenceCheckRef.current = window.setInterval(check, 100) as unknown as number;
    }, 1500);
  }, []);

  const stopRecording = useCallback(() => {
    if (silenceCheckRef.current) {
      clearInterval(silenceCheckRef.current);
      silenceCheckRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
      analyserRef.current = null;
    }
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setState((s) => ({ ...s, isRecording: false }));
  }, []);

  const stopSpeaking = useCallback(() => {
    stopAllAudio();
    setState((s) => ({ ...s, isSpeaking: false }));
  }, []);

  const processVoiceRoundTrip = useCallback(
    async (audioBlob: Blob) => {
      setState((s) => ({ ...s, isProcessing: true }));

      try {
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.webm");
        if (store.activeConversationId) {
          formData.append("conversation_id", store.activeConversationId);
        }
        if (projectId) {
          formData.append("project_id", projectId);
        }

        const response = await fetch(VOICE_CHAT_URL, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Voice chat failed: ${response.statusText}`);
        }

        const data: VoiceChatResponse = await response.json();

        if (data.conversation_id && !store.activeConversationId) {
          store.setActiveConversation(data.conversation_id);
        }
        if (data.phase) {
          store.setCurrentPhase(data.phase);
        }

        const userMsg: Message = {
          id: crypto.randomUUID(),
          role: "user",
          content: data.transcript,
          timestamp: new Date().toISOString(),
          metadata: { voice: true },
        };
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.reply,
          agentName: data.agent_name,
          timestamp: new Date().toISOString(),
          metadata: { voice: true, phase: data.phase },
        };
        store.addMessage(userMsg);
        store.addMessage(assistantMsg);

        // Use backend summary if available, otherwise trim locally
        const spokenText = data.spoken_summary || trimForSpeech(data.reply);

        setState((s) => ({
          ...s,
          isProcessing: false,
          isSpeaking: true,
        }));

        try {
          await speak(spokenText, data.audio_base64);
        } catch {
          // TTS failed silently
        }

        setState((s) => ({ ...s, isSpeaking: false }));

        // Loop: auto-start recording again after speaking
        if (loopActiveRef.current) {
          // Small pause before next listen
          await new Promise((r) => setTimeout(r, 400));
          if (loopActiveRef.current) {
            startRecording();
          }
        }
      } catch (e) {
        setState((s) => ({
          ...s,
          isProcessing: false,
          error: e instanceof Error ? e.message : "Voice chat failed",
        }));
        // Even on error, keep the loop going
        if (loopActiveRef.current) {
          await new Promise((r) => setTimeout(r, 1500));
          if (loopActiveRef.current) {
            startRecording();
          }
        }
      }
    },
    [store, projectId],
  );

  /** Start the continuous voice conversation loop with a greeting */
  const startLoop = useCallback(async () => {
    loopActiveRef.current = true;
    setState((s) => ({ ...s, isLoopActive: true, error: null }));
    startRecording();
  }, [startRecording]);

  /** Stop the entire loop */
  const stopLoop = useCallback(() => {
    loopActiveRef.current = false;
    stopAllAudio();
    cleanup();
    setState({
      isRecording: false,
      isProcessing: false,
      isSpeaking: false,
      isLoopActive: false,
      error: null,
    });
  }, [cleanup]);

  return {
    ...state,
    startLoop,
    stopLoop,
    stopRecording,
    stopSpeaking,
    messages: store.messages,
    activeAgent: store.activeAgent,
    currentPhase: store.currentPhase,
  };
}
