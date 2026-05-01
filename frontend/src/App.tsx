import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import ChatView from "./components/chat/ChatView";
import ProjectList from "./components/projects/ProjectList";
import ProjectCreate from "./components/projects/ProjectCreate";
import ProjectDetail from "./components/projects/ProjectDetail";
import DeliverableView from "./components/agents/DeliverableView";

// Dashboard pages (from Cloover AI Sales Coach)
import HomePage from "./pages/HomePage";
import FormPage from "./pages/FormPage";
import ReportPage from "./pages/ReportPage";
import LeadDetailPage from "./pages/LeadDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Dashboard / Sales Coach pages (standalone layout) */}
        <Route path="/" element={<HomePage />} />
        <Route path="/form" element={<FormPage />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/lead/:id" element={<LeadDetailPage />} />

        {/* Agent chat and project pages (sidebar layout) */}
        <Route element={<Layout />}>
          <Route path="/chat" element={<ChatView />} />
          <Route path="/chat/:conversationId" element={<ChatView />} />

          <Route path="/projects" element={<ProjectList />} />
          <Route path="/projects/new" element={<ProjectCreate />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />

          <Route path="/projects/:projectId/chat" element={<ChatView />} />
          <Route path="/projects/:projectId/deliverable" element={<DeliverableView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
