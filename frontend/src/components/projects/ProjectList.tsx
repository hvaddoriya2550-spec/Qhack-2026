import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { api } from "../../services/api";
import type { Project } from "../../types/project";

const STATUS_COLORS: Record<string, string> = {
  gathering: "bg-[#3535F3]",
  researching: "bg-[#4747F5]",
  strategizing: "bg-[#5555F7]",
  complete: "bg-[#3535F3]",
};

export default function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.projects
      .list()
      .then(setProjects)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8 text-gray-400">Loading projects...</div>;
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Sales Projects</h1>
        <Link
          to="/projects/new"
          className="flex items-center gap-2 px-4 py-2 bg-[#3535F3] rounded-lg hover:bg-[#2828D0] transition text-sm"
        >
          <Plus className="w-4 h-4" /> New Project
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg mb-2">No projects yet</p>
          <p className="text-sm">Create your first sales project to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {projects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="block p-5 bg-gray-900 rounded-xl border border-gray-800 hover:border-gray-600 transition"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="font-semibold text-lg">{project.name}</h2>
                  {project.company_name && (
                    <p className="text-gray-400 text-sm mt-1">{project.company_name}</p>
                  )}
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[project.status] ?? "bg-gray-600"}`}
                >
                  {project.status}
                </span>
              </div>
              <p className="text-gray-500 text-xs mt-3">
                Updated {new Date(project.updated_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
