import { useCallback, useRef, useState } from "react";

const TRANSCRIBE_URL = "/api/v1/voice/transcribe";

export function useVoiceInput() {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        // Stop all tracks to release the mic
        stream.getTracks().forEach((t) => t.stop());

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setIsTranscribing(true);

        try {
          const formData = new FormData();
          formData.append("audio", blob, "recording.webm");

          const response = await fetch(TRANSCRIBE_URL, {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            throw new Error(`Transcription failed: ${response.statusText}`);
          }

          const data = await response.json();
          setTranscript(data.text);
        } catch {
          setTranscript(null);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setIsRecording(false);
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, []);

  const clearTranscript = useCallback(() => {
    setTranscript(null);
  }, []);

  return {
    isRecording,
    isTranscribing,
    transcript,
    startRecording,
    stopRecording,
    clearTranscript,
  };
}
