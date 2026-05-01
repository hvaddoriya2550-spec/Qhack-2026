import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { Download, ArrowLeft } from "lucide-react";
import { api } from "../../services/api";
import type { Deliverable } from "../../types/project";

export default function DeliverableView() {
  const { projectId } = useParams<{ projectId: string }>();
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [active, setActive] = useState<Deliverable | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    api.deliverables
      .listByProject(projectId)
      .then((list) => {
        setDeliverables(list);
        if (list.length > 0 && list[0]) {
          // Fetch full content for the latest
          api.deliverables.get(list[0].id).then(setActive);
        }
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <div className="p-8 text-gray-400">Loading deliverable...</div>;

  if (!active) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <Link to={`/projects/${projectId}`} className="flex items-center gap-2 text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Project
        </Link>
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg mb-2">No pitch deck yet</p>
          <p className="text-sm">Complete all phases in the chat to generate a pitch deck.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <Link
          to={`/projects/${projectId}`}
          className="flex items-center gap-2 text-gray-400 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Project
        </Link>
        <a
          href={api.deliverables.downloadUrl(active.id)}
          className="flex items-center gap-2 px-4 py-2 bg-[#3535F3] rounded-lg text-sm hover:bg-[#2828D0] transition"
        >
          <Download className="w-4 h-4" /> Download Markdown
        </a>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 prose prose-invert max-w-none">
        <ReactMarkdown>{active.content_markdown}</ReactMarkdown>
      </div>

      {deliverables.length > 1 && (
        <div className="mt-6">
          <h3 className="text-sm text-gray-400 mb-2">Previous versions</h3>
          <div className="space-y-2">
            {deliverables.slice(1).map((d) => (
              <button
                key={d.id}
                onClick={() => api.deliverables.get(d.id).then(setActive)}
                className="block text-sm text-gray-400 hover:text-white"
              >
                {d.title} - {new Date(d.created_at).toLocaleDateString()}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
