import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  MapPin,
  Users,
  Zap,
  Wallet,
  Home,
  Calendar,
  Flame,
  FileText,
  MessageCircle,
} from "lucide-react";

const leads = [
  {
    id: 1,
    name: "Markus Weber",
    postal_code: "74238",
    city: "Krautheim",
    product_interest: "Heat pump",
    household_size: 4,
    house_type: "Detached",
    build_year: 1985,
    electricity_kwh_year: 4500,
    heating_type: "Gas",
    monthly_energy_bill_eur: 180,
    financial_profile: "Mid-income, open to financing",
    notes: "Concerned about rising gas prices",
    date_of_birth: "1979-05-12",
  },
  {
    id: 2,
    name: "Anna Schneider",
    postal_code: "69120",
    city: "Heidelberg",
    product_interest: "Solar",
    household_size: 2,
    house_type: "Semi-detached",
    build_year: 1998,
    electricity_kwh_year: 3200,
    heating_type: "Gas",
    monthly_energy_bill_eur: 120,
    financial_profile: "High income, prefers cash",
    notes: "Interested in sustainability",
    date_of_birth: "1987-09-03",
  },
  {
    id: 3,
    name: "Sabine Keller",
    postal_code: "74523",
    city: "Schwäbisch Hall",
    product_interest: "Heat pump + Solar",
    household_size: 5,
    house_type: "Detached",
    build_year: 1978,
    electricity_kwh_year: 6000,
    heating_type: "Oil",
    monthly_energy_bill_eur: 260,
    financial_profile: "Needs financing",
    notes: "Wants to replace oil heating",
    date_of_birth: "1972-02-14",
  },
  {
    id: 4,
    name: "Daniel Braun",
    postal_code: "74072",
    city: "Heilbronn",
    product_interest: "Solar + Battery + Wallbox",
    household_size: 2,
    house_type: "Detached",
    build_year: 2012,
    electricity_kwh_year: 3500,
    heating_type: "Heat pump",
    monthly_energy_bill_eur: 140,
    financial_profile: "High income",
    notes: "Just bought an EV",
    date_of_birth: "1990-07-08",
  },
  {
    id: 5,
    name: "Petra Lange",
    postal_code: "70563",
    city: "Stuttgart",
    product_interest: "Heat pump",
    household_size: 4,
    house_type: "Detached",
    build_year: 1970,
    electricity_kwh_year: 5200,
    heating_type: "Oil",
    monthly_energy_bill_eur: 250,
    financial_profile: "Financing required",
    notes: "Has solar, worried about oil prices",
    date_of_birth: "1950-11-02",
  },
];

export default function FormPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);

  const [allProjects, setAllProjects] = useState([]);

  // Fetch all projects
  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL || ""}/api/v1/projects/`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setAllProjects(data);
          // Filter out projects that match hardcoded lead names
          const leadNames = leads.map((l) => l.name);
          const chatProjects = data.filter((p) => !leadNames.includes(p.name));
          setProjects(chatProjects);
        }
      })
      .catch(() => {});
  }, []);

  // Get project status for a hardcoded lead
  const getLeadStatus = (lead) => {
    const proj = allProjects.find((p) => p.customer_name === lead.name || p.name === lead.name);
    return proj?.status || null;
  };

  const formatProduct = (value) => {
    if (!value) return "—";
    return value
      .replace(/_/g, " ")
      .split(" ")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-bg-glow dashboard-glow-1"></div>
      <div className="dashboard-bg-glow dashboard-glow-2"></div>
      <div className="dashboard-grid-overlay"></div>

      <div className="dashboard-container">
        {/* Header */}
        <motion.div
          className="dashboard-header"
          initial={{ opacity: 0, y: -18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="dashboard-header-left">
            <motion.button
              onClick={() => navigate("/")}
              whileHover={{ x: -2 }}
              whileTap={{ scale: 0.95 }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                padding: "6px 12px",
                borderRadius: "8px",
                background: "transparent",
                border: "none",
                color: "#64748b",
                fontWeight: 500,
                fontSize: "0.85rem",
                cursor: "pointer",
                marginBottom: "16px",
              }}
            >
              <ArrowLeft size={15} />
              Back
            </motion.button>

            <div>
              <p className="dashboard-kicker" style={{ marginBottom: "4px" }}>Lead Qualification Workspace</p>
              <h1 style={{ margin: "0 0 6px", fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.03em", textAlign: "left" }}>Sales Dashboard</h1>
              <p className="dashboard-subtitle" style={{ textAlign: "left", margin: 0 }}>
                Select a lead to review their profile and start a coaching session with Cleo.
              </p>
            </div>
          </div>

          <motion.button
            className="primary-btn"
            onClick={() => navigate("/chat")}
            whileHover={{ scale: 1.02, boxShadow: "0 8px 30px rgba(53,53,243,0.3)" }}
            whileTap={{ scale: 0.97 }}
            style={{ display: "flex", alignItems: "center", gap: "8px", minHeight: "46px", padding: "0 20px" }}
          >
            <MessageCircle size={18} />
            Talk to Cleo
          </motion.button>
        </motion.div>

        {/* Lead Cards */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.08 }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 700 }}>All Leads</h2>
            <span style={{ color: "#64748b", fontSize: "0.9rem" }}>{leads.length + projects.length} profiles</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {leads.map((lead, i) => (
              <motion.button
                key={lead.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08, duration: 0.4, ease: "easeOut" }}
                whileHover={{ y: -3, boxShadow: "0 12px 40px rgba(53,53,243,0.08)" }}
                whileTap={{ scale: 0.99 }}
                onClick={() => navigate(`/lead/${lead.id}`)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "24px",
                  borderRadius: "20px",
                  background: "#ffffff",
                  border: "1px solid #e5e7eb",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
                  cursor: "pointer",
                  transition: "border-color 0.2s",
                }}
              >
                {/* Card Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
                  <div>
                    <h3 style={{ margin: "0 0 4px", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>{lead.name}</h3>
                    <p style={{ margin: 0, color: "#3535F3", fontSize: "0.9rem", fontWeight: 600 }}>{formatProduct(lead.product_interest)}</p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    {(() => {
                      const st = getLeadStatus(lead);
                      const isDone = st === "complete" || st === "deliverable";
                      return (
                        <span style={{
                          padding: "6px 12px",
                          borderRadius: "999px",
                          fontSize: "0.78rem",
                          fontWeight: 600,
                          background: isDone ? "rgba(34,197,94,0.1)" : "rgba(53,53,243,0.08)",
                          color: isDone ? "#16a34a" : "#3535F3",
                          border: `1px solid ${isDone ? "rgba(34,197,94,0.2)" : "rgba(53,53,243,0.15)"}`,
                        }}>
                          {isDone ? "Report Ready" : st ? "In Progress" : "Active Lead"}
                        </span>
                      );
                    })()}
                    <ArrowRight size={16} style={{ color: "#94a3b8" }} />
                  </div>
                </div>

                {/* Card Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                  {[
                    { icon: <MapPin size={14} />, label: "City", value: lead.city },
                    { icon: <MapPin size={14} />, label: "Postal", value: lead.postal_code },
                    { icon: <Users size={14} />, label: "Household", value: `${lead.household_size} people` },
                    { icon: <Zap size={14} />, label: "Electricity", value: `${lead.electricity_kwh_year} kWh` },
                    { icon: <Wallet size={14} />, label: "Budget", value: lead.financial_profile },
                    { icon: <Home size={14} />, label: "House", value: lead.house_type || "—" },
                    { icon: <Flame size={14} />, label: "Heating", value: lead.heating_type },
                    { icon: <Calendar size={14} />, label: "Built", value: lead.build_year || "—" },
                  ].map((item, j) => (
                    <div key={j} style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "10px 12px",
                      borderRadius: "12px",
                      background: "#f8f9fb",
                      border: "1px solid #f1f5f9",
                    }}>
                      <span style={{ color: "#94a3b8", flexShrink: 0 }}>{item.icon}</span>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: "0.7rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>{item.label}</div>
                        <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.value}</div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Notes row */}
                {lead.notes && (
                  <div style={{
                    marginTop: "12px",
                    padding: "10px 14px",
                    borderRadius: "12px",
                    background: "#f8f9fb",
                    border: "1px solid #f1f5f9",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}>
                    <FileText size={14} style={{ color: "#94a3b8", flexShrink: 0 }} />
                    <span style={{ fontSize: "0.85rem", color: "#475569" }}>{lead.notes}</span>
                  </div>
                )}
              </motion.button>
            ))}

            {/* Chat-created projects in same list */}
              {projects.map((proj, i) => {
                const isDone = proj.status === "complete" || proj.status === "deliverable";
                return (
                  <motion.button
                    key={proj.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.08, duration: 0.4 }}
                    whileHover={{ y: -3, boxShadow: "0 12px 40px rgba(53,53,243,0.08)" }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => navigate(`/projects/${proj.id}/chat`)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "24px",
                      borderRadius: "20px",
                      background: "#ffffff",
                      border: "1px solid #e5e7eb",
                      boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
                      cursor: "pointer",
                    }}
                  >
                    {/* Header */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
                      <div>
                        <h3 style={{ margin: "0 0 4px", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
                          {proj.customer_name || proj.name || "Untitled Project"}
                        </h3>
                        <p style={{ margin: 0, color: "#3535F3", fontSize: "0.9rem", fontWeight: 600 }}>
                          {formatProduct(proj.product_interest) || "Energy Solutions"}
                        </p>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{
                          padding: "6px 12px",
                          borderRadius: "999px",
                          fontSize: "0.78rem",
                          fontWeight: 600,
                          background: isDone ? "rgba(34,197,94,0.1)" : "rgba(53,53,243,0.08)",
                          color: isDone ? "#16a34a" : "#3535F3",
                          border: `1px solid ${isDone ? "rgba(34,197,94,0.2)" : "rgba(53,53,243,0.15)"}`,
                        }}>
                          {isDone ? "Report Ready" : "In Progress"}
                        </span>
                        <ArrowRight size={16} style={{ color: "#94a3b8" }} />
                      </div>
                    </div>

                    {/* Data grid — same as lead cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                      {[
                        { icon: <MapPin size={14} />, label: "City", value: proj.city || "—" },
                        { icon: <MapPin size={14} />, label: "Postal", value: proj.postal_code || "—" },
                        { icon: <Users size={14} />, label: "Household", value: proj.household_size ? `${proj.household_size} people` : "—" },
                        { icon: <Zap size={14} />, label: "Electricity", value: proj.electricity_kwh_year ? `${proj.electricity_kwh_year} kWh` : "—" },
                        { icon: <Wallet size={14} />, label: "Budget", value: proj.financial_profile || "—" },
                        { icon: <Home size={14} />, label: "House", value: proj.house_type || "—" },
                        { icon: <Flame size={14} />, label: "Heating", value: proj.heating_type || "—" },
                        { icon: <Calendar size={14} />, label: "Built", value: proj.build_year || "—" },
                      ].map((item, j) => (
                        <div key={j} style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "10px 12px",
                          borderRadius: "12px",
                          background: "#f8f9fb",
                          border: "1px solid #f1f5f9",
                        }}>
                          <span style={{ color: "#94a3b8", flexShrink: 0 }}>{item.icon}</span>
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontSize: "0.7rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>{item.label}</div>
                            <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.value}</div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Notes */}
                    {proj.notes && (
                      <div style={{
                        marginTop: "12px",
                        padding: "10px 14px",
                        borderRadius: "12px",
                        background: "#f8f9fb",
                        border: "1px solid #f1f5f9",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}>
                        <FileText size={14} style={{ color: "#94a3b8", flexShrink: 0 }} />
                        <span style={{ fontSize: "0.85rem", color: "#475569" }}>{proj.notes}</span>
                      </div>
                    )}
                  </motion.button>
                );
              })}
          </div>
        </motion.div>
      </div>

      {/* Floating Chat Button */}
      <motion.button
        onClick={() => navigate("/chat")}
        style={{
          position: "fixed",
          bottom: "28px",
          right: "28px",
          width: "56px",
          height: "56px",
          borderRadius: "50%",
          background: "linear-gradient(135deg, #3535F3, #4747F5)",
          color: "white",
          border: "none",
          boxShadow: "0 8px 30px rgba(53,53,243,0.35)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 50,
        }}
        whileHover={{ scale: 1.1, boxShadow: "0 12px 40px rgba(53,53,243,0.45)" }}
        whileTap={{ scale: 0.95 }}
      >
        <MessageCircle size={24} />
      </motion.button>
    </div>
  );
}
