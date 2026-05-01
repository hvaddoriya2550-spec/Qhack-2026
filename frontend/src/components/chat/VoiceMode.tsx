import clsx from "clsx";
import { useVoiceChat } from "../../hooks/useVoiceChat";

interface Props {
  projectId?: string;
}

export default function VoiceMode({ projectId }: Props) {
  const {
    isRecording,
    isProcessing,
    isSpeaking,
    isLoopActive,
    error,
    startLoop,
    stopLoop,
  } = useVoiceChat(projectId);

  const handleMainClick = () => {
    if (isLoopActive) stopLoop();
    else startLoop();
  };

  let statusText = "Tap Cleo to start";
  if (isRecording) statusText = "Listening...";
  if (isProcessing) statusText = "Thinking...";
  if (isSpeaking) statusText = "Speaking...";
  if (error) statusText = error;

  const state = isRecording
    ? "recording"
    : isProcessing
      ? "processing"
      : isSpeaking
        ? "speaking"
        : isLoopActive
          ? "idle-active"
          : "idle";

  return (
    <div className="flex flex-col items-center justify-center flex-1 relative overflow-hidden select-none">
      {/* Click target */}
      <button onClick={handleMainClick} className="relative z-10 focus:outline-none group">
        {/* Outer aura */}
        <div
          className={clsx(
            "absolute rounded-full transition-all duration-700 -inset-8",
            state === "recording" && "animate-ping bg-red-500/15",
            state === "processing" && "animate-pulse bg-[#3535F3]/10",
            state === "speaking" && "animate-pulse bg-[#3535F3]/15",
          )}
        />
        <div
          className={clsx(
            "absolute rounded-full transition-all duration-500 -inset-4",
            state === "recording" && "animate-pulse bg-red-500/10",
            state === "speaking" && "animate-pulse bg-[#3535F3]/10",
          )}
        />

        {/* Avatar container */}
        <div
          className={clsx(
            "w-44 h-44 rounded-full relative transition-all duration-500",
            state === "idle" && "hover:scale-105",
            state === "recording" && "scale-105",
            state === "speaking" && "scale-105",
          )}
        >
          {/* Face background */}
          <div
            className={clsx(
              "absolute inset-0 rounded-full transition-all duration-500",
              state === "idle" && "bg-gradient-to-br from-[#3535F3] via-[#2828D0] to-[#1a1a8f] shadow-xl shadow-[#3535F3]/20",
              state === "idle-active" && "bg-gradient-to-br from-gray-400 to-gray-600 shadow-xl shadow-gray-500/20",
              state === "recording" && "bg-gradient-to-br from-[#4040F5] via-[#3535F3] to-[#2020B0] shadow-xl shadow-red-500/30",
              state === "processing" && "bg-gradient-to-br from-[#4747F5] via-[#3535F3] to-[#2828D0] shadow-xl shadow-[#3535F3]/30",
              state === "speaking" && "bg-gradient-to-br from-[#5050F7] via-[#3535F3] to-[#2020A0] shadow-xl shadow-[#3535F3]/30",
            )}
          />

          {/* Face shine */}
          <div className="absolute inset-0 rounded-full overflow-hidden">
            <div className="absolute top-0 left-1/4 w-1/2 h-1/3 bg-gradient-to-b from-white/15 to-transparent rounded-full blur-sm" />
          </div>

          {/* Eyes */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex gap-7 -mt-3">
              {/* Left eye */}
              <div className="relative">
                <div
                  className={clsx(
                    "w-4 rounded-full bg-white transition-all duration-300",
                    state === "processing" ? "h-1 mt-1.5" : "h-4",
                    state === "speaking" && "animate-[blink_3s_ease-in-out_infinite]",
                  )}
                />
                {/* Pupil */}
                {state !== "processing" && (
                  <div
                    className={clsx(
                      "absolute w-2 h-2 rounded-full bg-[#0a0a2e] top-1 left-1 transition-all duration-300",
                      state === "recording" && "bg-red-900",
                      state === "speaking" && "animate-[lookAround_4s_ease-in-out_infinite]",
                    )}
                  />
                )}
                {/* Eye glow */}
                {(state === "recording" || state === "speaking") && (
                  <div className={clsx(
                    "absolute w-1 h-1 rounded-full top-0.5 left-2.5",
                    state === "recording" ? "bg-red-300" : "bg-blue-200",
                  )} />
                )}
              </div>

              {/* Right eye */}
              <div className="relative">
                <div
                  className={clsx(
                    "w-4 rounded-full bg-white transition-all duration-300",
                    state === "processing" ? "h-1 mt-1.5" : "h-4",
                    state === "speaking" && "animate-[blink_3s_ease-in-out_0.1s_infinite]",
                  )}
                />
                {state !== "processing" && (
                  <div
                    className={clsx(
                      "absolute w-2 h-2 rounded-full bg-[#0a0a2e] top-1 left-1 transition-all duration-300",
                      state === "recording" && "bg-red-900",
                      state === "speaking" && "animate-[lookAround_4s_ease-in-out_infinite]",
                    )}
                  />
                )}
                {(state === "recording" || state === "speaking") && (
                  <div className={clsx(
                    "absolute w-1 h-1 rounded-full top-0.5 left-2.5",
                    state === "recording" ? "bg-red-300" : "bg-blue-200",
                  )} />
                )}
              </div>
            </div>
          </div>

          {/* Mouth */}
          <div className="absolute bottom-10 left-1/2 -translate-x-1/2">
            {state === "speaking" ? (
              /* Animated speaking mouth */
              <div className="flex items-end gap-[2px]">
                {[0, 1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="w-[4px] rounded-full bg-white/90"
                    style={{
                      animation: `mouthBar 0.4s ease-in-out ${i * 0.06}s infinite alternate`,
                    }}
                  />
                ))}
              </div>
            ) : state === "recording" ? (
              /* Open mouth - listening */
              <div className="w-5 h-5 rounded-full border-2 border-white/80 bg-white/10 animate-pulse" />
            ) : state === "processing" ? (
              /* Thinking mouth - flat line */
              <div className="w-6 h-[2px] rounded-full bg-white/50" />
            ) : (
              /* Idle smile */
              <div className="w-8 h-3 border-b-2 border-white/70 rounded-b-full" />
            )}
          </div>

          {/* Processing spinner ring */}
          {state === "processing" && (
            <div className="absolute inset-0 rounded-full border-[3px] border-white/10 border-t-white/40 animate-spin" />
          )}
        </div>
      </button>

      {/* Name */}
      <p className="mt-6 text-base font-bold text-gray-800 relative z-10">Cleo</p>

      {/* Status */}
      <p
        className={clsx(
          "mt-1 text-sm relative z-10 transition-colors duration-300",
          error ? "text-red-500 font-medium" : "text-gray-500",
        )}
      >
        {statusText}
      </p>

      {isLoopActive && !isRecording && !isProcessing && !isSpeaking && (
        <p className="mt-1 text-[10px] uppercase tracking-widest text-gray-400 relative z-10">
          Tap to end
        </p>
      )}

      {/* Animations */}
      <style>{`
        @keyframes mouthBar {
          0% { height: 4px; }
          100% { height: 14px; }
        }
        @keyframes blink {
          0%, 90%, 100% { transform: scaleY(1); }
          95% { transform: scaleY(0.1); }
        }
        @keyframes lookAround {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(1px); }
          75% { transform: translateX(-1px); }
        }
      `}</style>
    </div>
  );
}
