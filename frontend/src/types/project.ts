export interface Project {
  id: string;
  name: string;
  company_name: string | null;
  company_description: string | null;
  industry: string | null;
  products: unknown[];
  target_market: string | null;
  competitors: unknown[];
  research_data: Record<string, unknown>;
  strategy_notes: Record<string, unknown>;
  status: "gathering" | "researching" | "strategizing" | "complete";
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  company_name?: string;
  company_description?: string;
  industry?: string;
  target_market?: string;
}

export interface Deliverable {
  id: string;
  project_id: string;
  title: string;
  content_markdown: string;
  created_at: string;
}
