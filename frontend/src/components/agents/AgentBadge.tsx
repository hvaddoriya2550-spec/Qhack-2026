import clsx from "clsx";

const AGENT_STYLES: Record<string, { color: string; label: string }> = {
  data_gathering: { color: "bg-[#3535F3]", label: "Data Gathering" },
  research: { color: "bg-[#4747F5]", label: "Research" },
  analysis: { color: "bg-[#5757F7]", label: "Analysis" },
  financial: { color: "bg-[#6262FB]", label: "Financial" },
  strategy: { color: "bg-[#6565FF]", label: "Strategy" },
  pitch_deck: { color: "bg-[#3535F3]", label: "Pitch Deck" },
};

interface Props {
  agentName: string;
  className?: string;
}

export default function AgentBadge({ agentName, className }: Props) {
  const style = AGENT_STYLES[agentName] ?? { color: "bg-gray-600", label: agentName };

  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        style.color,
        className,
      )}
    >
      {style.label}
    </span>
  );
}
