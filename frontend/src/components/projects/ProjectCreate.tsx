import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../services/api";

export default function ProjectCreate() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [companyDescription, setCompanyDescription] = useState("");
  const [industry, setIndustry] = useState("");
  const [targetMarket, setTargetMarket] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);

    try {
      const project = await api.projects.create({
        name: name.trim(),
        company_name: companyName.trim() || undefined,
        company_description: companyDescription.trim() || undefined,
        industry: industry.trim() || undefined,
        target_market: targetMarket.trim() || undefined,
      });
      navigate(`/projects/${project.id}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">New Sales Project</h1>
      <p className="text-gray-400 text-sm mb-8">
        Pre-fill what you know. The AI agent will gather anything missing through conversation.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Field label="Project Name *" value={name} onChange={setName} placeholder="e.g., Q3 Enterprise Push" />
        <Field label="Company Name" value={companyName} onChange={setCompanyName} placeholder="Your company name" />
        <Field
          label="Company Description"
          value={companyDescription}
          onChange={setCompanyDescription}
          placeholder="What does your company do?"
          multiline
        />
        <Field label="Industry" value={industry} onChange={setIndustry} placeholder="e.g., SaaS, Healthcare, FinTech" />
        <Field
          label="Target Market"
          value={targetMarket}
          onChange={setTargetMarket}
          placeholder="Who are your ideal customers?"
          multiline
        />

        <div className="flex gap-3 pt-4">
          <button
            type="submit"
            disabled={!name.trim() || submitting}
            className="px-6 py-2 bg-[#3535F3] rounded-lg text-sm hover:bg-[#2828D0] disabled:opacity-50 transition"
          >
            {submitting ? "Creating..." : "Create Project"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/projects")}
            className="px-6 py-2 bg-gray-800 rounded-lg text-sm hover:bg-gray-700 transition"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  multiline,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  multiline?: boolean;
}) {
  const cls =
    "w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500";
  return (
    <div>
      <label className="block text-sm text-gray-300 mb-1">{label}</label>
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={3}
          className={cls}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={cls}
        />
      )}
    </div>
  );
}
