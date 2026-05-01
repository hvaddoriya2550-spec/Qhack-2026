import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { MessageSquare, FileText } from "lucide-react";
import { api } from "../../services/api";
import type { Project } from "../../types/project";
import PhaseIndicator from "../agents/PhaseIndicator";

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    api.projects
      .get(projectId)
      .then(setProject)
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;
  if (!project) return <div className="p-8 text-red-400">Project not found</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          {project.company_name && <p className="text-gray-400 mt-1">{project.company_name}</p>}
        </div>
        <Link
          to="/projects"
          className="text-sm text-gray-400 hover:text-white transition"
        >
          Back to Projects
        </Link>
      </div>

      <PhaseIndicator status={project.status} />

      <div className="grid grid-cols-2 gap-4 mt-8">
        <Link
          to={`/projects/${project.id}/chat`}
          className="flex items-center gap-3 p-5 bg-gray-900 rounded-xl border border-gray-800 hover:border-blue-600 transition"
        >
          <MessageSquare className="w-6 h-6 text-blue-500" />
          <div>
            <div className="font-medium">Start Chat</div>
            <div className="text-sm text-gray-400">Continue the sales conversation</div>
          </div>
        </Link>

        <Link
          to={`/projects/${project.id}/deliverable`}
          className="flex items-center gap-3 p-5 bg-gray-900 rounded-xl border border-gray-800 hover:border-[#3535F3] transition"
        >
          <FileText className="w-6 h-6 text-[#5555F7]" />
          <div>
            <div className="font-medium">Pitch Deck</div>
            <div className="text-sm text-gray-400">View generated report</div>
          </div>
        </Link>
      </div>

      {/* Data summary cards */}
      <div className="mt-8 space-y-4">
        {project.company_description && (
          <InfoCard title="About" content={project.company_description} />
        )}
        {project.target_market && (
          <InfoCard title="Target Market" content={project.target_market} />
        )}
        {project.industry && (
          <InfoCard title="Industry" content={project.industry} />
        )}
      </div>
    </div>
  );
}

function InfoCard({ title, content }: { title: string; content: string }) {
  return (
    <div className="p-4 bg-gray-900 rounded-xl border border-gray-800">
      <h3 className="text-sm font-medium text-gray-400 mb-1">{title}</h3>
      <p className="text-sm">{content}</p>
    </div>
  );
}
