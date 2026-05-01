import clsx from "clsx";
import {
  ClipboardList,
  Search,
  Sun,
  Wallet,
  Lightbulb,
  FileText,
  Check,
} from "lucide-react";

const PHASES = [
  { key: "gathering", label: "Lead", icon: ClipboardList },
  { key: "researching", label: "Research", icon: Search },
  { key: "analyzing", label: "Analysis", icon: Sun },
  { key: "financing", label: "Financing", icon: Wallet },
  { key: "strategizing", label: "Strategy", icon: Lightbulb },
  { key: "complete", label: "Report", icon: FileText },
];

interface Props {
  status: string;
}

export default function PhaseIndicator({ status }: Props) {
  const currentIndex = PHASES.findIndex((p) => p.key === status);

  return (
    <div className="w-full">
      {/* Circles + connectors row */}
      <div className="flex items-center w-full">
        {PHASES.map((phase, i) => {
          const isComplete = i < currentIndex;
          const isCurrent = i === currentIndex;
          const Icon = phase.icon;

          return (
            <div key={phase.key} className="contents">
              {/* Connector before (except first) */}
              {i > 0 && (
                <div className="flex-1 h-[2px] rounded-full relative overflow-hidden" style={{ background: "#e5e7eb" }}>
                  <div
                    className={clsx(
                      "absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out",
                      isCurrent && "animate-pulse",
                    )}
                    style={{
                      width: isComplete || isCurrent ? "100%" : "0%",
                      background: isComplete ? "#22c55e" : isCurrent ? "#3535F3" : "transparent",
                    }}
                  />
                </div>
              )}

              {/* Circle */}
              <div
                className={clsx(
                  "w-9 h-9 rounded-full flex items-center justify-center transition-all duration-500 text-xs shrink-0",
                  isComplete && "bg-[#22c55e] text-white",
                  isCurrent && "bg-[#3535F3] text-white ring-4 ring-[#3535F3]/25 animate-pulse",
                  !isComplete && !isCurrent && "bg-gray-100 text-gray-400 border border-gray-200",
                )}
              >
                {isComplete ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
              </div>
            </div>
          );
        })}
      </div>

      {/* Labels row */}
      <div className="flex w-full mt-1.5">
        {PHASES.map((phase, i) => {
          const isComplete = i < currentIndex;
          const isCurrent = i === currentIndex;

          return (
            <div key={phase.key} className="contents">
              {i > 0 && <div className="flex-1" />}
              <div className="w-9 shrink-0 text-center">
                <span
                  className={clsx(
                    "text-[9px] font-semibold tracking-wider uppercase",
                    isComplete && "text-[#22c55e]",
                    isCurrent && "text-[#3535F3]",
                    !isComplete && !isCurrent && "text-gray-400",
                  )}
                >
                  {phase.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
