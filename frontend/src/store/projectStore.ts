import { create } from "zustand";
import type { Project } from "../types/project";

interface ProjectState {
  projects: Project[];
  activeProjectId: string | null;

  setProjects: (projects: Project[]) => void;
  setActiveProject: (id: string | null) => void;
  updateProject: (project: Project) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  activeProjectId: null,

  setProjects: (projects) => set({ projects }),
  setActiveProject: (id) => set({ activeProjectId: id }),
  updateProject: (project) =>
    set((state) => ({
      projects: state.projects.map((p) => (p.id === project.id ? project : p)),
    })),
}));
