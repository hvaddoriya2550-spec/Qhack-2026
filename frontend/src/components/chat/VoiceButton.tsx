import { Mic, MicOff, Loader2 } from "lucide-react";
import clsx from "clsx";

interface Props {
  isRecording: boolean;
  isTranscribing: boolean;
  onToggle: () => void;
}

export default function VoiceButton({ isRecording, isTranscribing, onToggle }: Props) {
  if (isTranscribing) {
    return (
      <button
        type="button"
        disabled
        className="p-2 rounded-xl text-gray-400"
        title="Transcribing..."
      >
        <Loader2 className="w-5 h-5 animate-spin" />
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onToggle}
      className={clsx(
        "p-2 rounded-xl transition",
        isRecording
          ? "bg-red-600 text-white animate-pulse hover:bg-red-700"
          : "text-gray-400 hover:text-white hover:bg-gray-800",
      )}
      title={isRecording ? "Stop recording" : "Start voice input"}
    >
      {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
    </button>
  );
}
