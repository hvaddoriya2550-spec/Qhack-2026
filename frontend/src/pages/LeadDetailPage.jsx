import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  MapPin,
  Users,
  Zap,
  Wallet,
  Target,
  MessageCircle,
  Home,
  Calendar,
  Flame,
  FileText,
  Paperclip,
  Upload,
  Loader2,
  File,
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
    roof_orientation: "South",
    electricity_kwh_year: 4500,
    heating_type: "Gas",
    monthly_energy_bill_eur: 180,
    existing_assets: "None",
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
    roof_orientation: "South-East",
    electricity_kwh_year: 3200,
    heating_type: "Gas",
    monthly_energy_bill_eur: 120,
    existing_assets: "None",
    financial_profile: "High income, prefers cash",
    notes: "Interested in sustainability and reducing carbon footprint",
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
    roof_orientation: "South-West",
    electricity_kwh_year: 6000,
    heating_type: "Oil",
    monthly_energy_bill_eur: 260,
    existing_assets: "None",
    financial_profile: "Limited upfront budget, needs financing",
    notes: "Large roof area, wants to replace oil heating before regulations hit",
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
    roof_orientation: "South",
    electricity_kwh_year: 3500,
    heating_type: "Heat pump",
    monthly_energy_bill_eur: 140,
    existing_assets: "None",
    financial_profile: "High income, prefers full package",
    notes: "Just bought an EV, wants full energy independence",
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
    roof_orientation: "South-West",
    electricity_kwh_year: 5200,
    heating_type: "Oil",
    monthly_energy_bill_eur: 250,
    existing_assets: "Solar 5 kWp",
    financial_profile: "Financing required",
    notes: "Already has solar, concerned about oil price volatility and GEG deadline",
    date_of_birth: "1950-11-02",
  },
];

function DocumentsCard({ projectId, ensureProject }) {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  // Load existing docs when projectId is available
  useEffect(() => {
    if (!projectId) return;
    fetch(`${import.meta.env.VITE_API_URL || ""}/api/v1/documents/${projectId}`)
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setDocs(data); })
      .catch(() => {});
  }, [projectId]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const pid = await ensureProject();
      if (!pid) {
        alert("Could not create project for upload");
        return;
      }
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(
        `${import.meta.env.VITE_API_URL || ""}/api/v1/documents/upload/${pid}`,
        { method: "POST", body: formData },
      );
      if (res.ok) {
        const data = await res.json();
        setDocs((prev) => [...prev, { filename: data.filename, chars: data.chars, uploaded_at: new Date().toISOString() }]);
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Upload failed");
      }
    } catch (ex) {
      alert("Upload failed: " + (ex instanceof Error ? ex.message : "Unknown error"));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div style={{
      padding: "28px", borderRadius: "20px", background: "#ffffff",
      border: "1px solid #e5e7eb", boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <p style={{ margin: "0 0 4px", fontSize: "0.7rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "#3535F3", fontWeight: 700 }}>
            Documents
          </p>
          <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
            Uploaded Files
          </h3>
        </div>
        <input ref={fileRef} type="file" accept=".pdf" onChange={handleUpload} style={{ display: "none" }} />
        <motion.button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.95 }}
          style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            padding: "8px 14px", borderRadius: "10px",
            background: "#f8f9fb", border: "1px solid #e5e7eb",
            color: "#3535F3", fontSize: "0.82rem", fontWeight: 600,
            cursor: uploading ? "not-allowed" : "pointer",
          }}
        >
          {uploading ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Upload size={14} />}
          {uploading ? "Uploading..." : "Upload PDF"}
        </motion.button>
      </div>

      {docs.length === 0 ? (
        <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.88rem" }}>
          No documents uploaded yet. Upload product brochures, price lists, or spec sheets — Cleo will use them during research.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {docs.map((doc, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: "10px",
              padding: "10px 14px", borderRadius: "12px",
              background: "#f8f9fb", border: "1px solid #f1f5f9",
            }}>
              <File size={16} style={{ color: "#3535F3", flexShrink: 0 }} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <p style={{ margin: 0, fontSize: "0.85rem", fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {doc.filename}
                </p>
                <p style={{ margin: 0, fontSize: "0.72rem", color: "#94a3b8" }}>
                  {Math.round((doc.chars || 0) / 100) / 10}k chars extracted
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function LeadPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  // Persist lead→project mapping in localStorage
  const [projectId, setProjectId] = useState(() => {
    return localStorage.getItem(`lead_project_${id}`) || null;
  });

  // Validate cached projectId — if the backend no longer knows it (DB was
  // recreated, project deleted, etc.) clear the stale reference so we can
  // create a fresh one on next action.
  useEffect(() => {
    if (!projectId) return;
    fetch(`${import.meta.env.VITE_API_URL || ""}/api/v1/projects/${projectId}`)
      .then((r) => {
        if (r.status === 404) {
          localStorage.removeItem(`lead_project_${id}`);
          setProjectId(null);
        }
      })
      .catch(() => {});
  }, [projectId, id]);

  const lead = useMemo(() => {
    return leads.find((item) => item.id === Number(id));
  }, [id]);

  // Create a project from lead data so the agent knows what's already collected
  const ensureProject = useCallback(async () => {
    if (projectId) return projectId;
    if (!lead) return null;

    const res = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/v1/projects/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: lead.name,
        customer_name: lead.name,
        date_of_birth: lead.date_of_birth || null,
        postal_code: lead.postal_code || lead.postcode,
        city: lead.city || lead.area,
        product_interest: lead.product_interest?.replace(/_/g, " + "),
        household_size: lead.household_size,
        house_type: lead.house_type || null,
        build_year: lead.build_year || null,
        roof_orientation: lead.roof_orientation || null,
        electricity_kwh_year: lead.electricity_kwh_year || lead.annual_consumption_kwh,
        heating_type: lead.heating_type || null,
        monthly_energy_bill_eur: lead.monthly_energy_bill_eur || null,
        existing_assets: lead.existing_assets || null,
        financial_profile: lead.financial_profile || lead.budget_band,
        notes: lead.notes || lead.customer_goal,
      }),
    });
    const project = await res.json();
    setProjectId(project.id);
    localStorage.setItem(`lead_project_${id}`, project.id);
    return project.id;
  }, [projectId, lead, id]);

  const handleOpenChat = useCallback(async () => {
    const pid = await ensureProject();
    navigate(`/projects/${pid}/chat`);
  }, [ensureProject, navigate]);

  const formatProduct = (value) => {
    if (!value) return "—";

    return value
      .replace(/_/g, " ")
      .split(" ")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  const getLeadLocation = (lead) => lead.city || lead.area || "—";
  const getLeadPostalCode = (lead) => lead.postal_code || lead.postcode || "—";
  const getLeadUsage = (lead) =>
    lead.electricity_kwh_year || lead.annual_consumption_kwh || "—";
  const getLeadBudget = (lead) =>
    lead.financial_profile || lead.budget_band || "—";
  const getLeadGoal = (lead) => lead.notes || lead.customer_goal || "—";

  const formatDob = (dob) => {
    if (!dob) return "—";
    const d = new Date(dob);
    if (Number.isNaN(d.getTime())) return dob;
    const today = new Date();
    let age = today.getFullYear() - d.getFullYear();
    const m = today.getMonth() - d.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < d.getDate())) age -= 1;
    return `${d.toLocaleDateString("en-GB")} (age ${age})`;
  };

  if (!lead) {
    return (
      <div className="lead-page">
        <div className="lead-page-container">
          <button className="back-link-btn" onClick={() => navigate("/form")}>
            <ArrowLeft size={18} />
            Back
          </button>

          <div className="lead-not-found-card">
            <h2>Lead not found</h2>
            <p>The requested customer profile does not exist.</p>
          </div>
        </div>
      </div>
    );
  }

  const dataItems = [
    { icon: <MapPin size={14} />, label: "City", value: getLeadLocation(lead) },
    { icon: <MapPin size={14} />, label: "Postal Code", value: getLeadPostalCode(lead) },
    { icon: <Users size={14} />, label: "Household", value: `${lead.household_size || "—"} people` },
    { icon: <Zap size={14} />, label: "Electricity", value: `${getLeadUsage(lead)} kWh` },
    { icon: <Wallet size={14} />, label: "Budget / Profile", value: getLeadBudget(lead) },
    { icon: <Target size={14} />, label: "Product Interest", value: formatProduct(lead.product_interest) },
    { icon: <Home size={14} />, label: "House Type", value: lead.house_type || "—" },
    { icon: <Calendar size={14} />, label: "Build Year", value: lead.build_year || "—" },
    { icon: <Calendar size={14} />, label: "Date of Birth", value: formatDob(lead.date_of_birth) },
    { icon: <MapPin size={14} />, label: "Roof", value: lead.roof_orientation || "—" },
    { icon: <Flame size={14} />, label: "Heating", value: lead.heating_type || "—" },
    { icon: <Wallet size={14} />, label: "Monthly Bill", value: lead.monthly_energy_bill_eur ? `€${lead.monthly_energy_bill_eur}` : "—" },
    { icon: <FileText size={14} />, label: "Existing Assets", value: lead.existing_assets || "—" },
  ];

  return (
    <div style={{ background: "#f9fafb", minHeight: "100vh", position: "relative" }}>
      {/* Grid overlay */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        backgroundImage: "linear-gradient(rgba(15,23,42,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(15,23,42,0.03) 1px, transparent 1px)",
        backgroundSize: "40px 40px",
        maskImage: "linear-gradient(to bottom, rgba(0,0,0,0.75), transparent 95%)",
      }} />

      <div style={{ position: "relative", zIndex: 1, maxWidth: "1100px", margin: "0 auto", padding: "40px 24px 60px" }}>
        {/* Back button */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <motion.button
            onClick={() => navigate("/form")}
            whileHover={{ x: -2 }}
            whileTap={{ scale: 0.95 }}
            style={{
              display: "inline-flex", alignItems: "center", gap: "5px",
              padding: "6px 12px", borderRadius: "8px", background: "transparent",
              border: "none", color: "#64748b", fontWeight: 500, fontSize: "0.85rem",
              cursor: "pointer", marginBottom: "24px",
            }}
          >
            <ArrowLeft size={15} />
            Back
          </motion.button>
        </motion.div>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px" }}
        >
          <div>
            <p style={{ margin: "0 0 4px", fontSize: "0.75rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "#3535F3", fontWeight: 700 }}>
              Lead Detail Workspace
            </p>
            <h1 style={{ margin: "0 0 6px", fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.03em", color: "#0f172a" }}>
              {lead.name}
            </h1>
            <p style={{ margin: 0, color: "#6b7280", fontSize: "0.95rem" }}>
              Review this customer profile and prepare the sales conversation.
            </p>
          </div>
        </motion.div>

        {/* Content */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.08 }}
          style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "24px" }}
        >
          {/* Left — Customer card */}
          <div style={{
            padding: "28px", borderRadius: "20px", background: "#ffffff",
            border: "1px solid #e5e7eb", boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <div>
                <p style={{ margin: "0 0 4px", fontSize: "0.7rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "#3535F3", fontWeight: 700 }}>
                  Customer Overview
                </p>
                <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 700, color: "#0f172a" }}>{lead.name}</h2>
              </div>
              <span style={{
                padding: "6px 12px", borderRadius: "999px", fontSize: "0.78rem", fontWeight: 600,
                background: "rgba(53,53,243,0.08)", color: "#3535F3", border: "1px solid rgba(53,53,243,0.15)",
              }}>
                Active Lead
              </span>
            </div>

            {/* Data grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              {dataItems.map((item, j) => (
                <div key={j} style={{
                  padding: "14px 16px", borderRadius: "14px", background: "#f8f9fb", border: "1px solid #f1f5f9",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                    <span style={{ color: "#94a3b8" }}>{item.icon}</span>
                    <span style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.04em" }}>{item.label}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: "0.92rem", fontWeight: 600, color: "#0f172a" }}>{item.value}</p>
                </div>
              ))}
            </div>

            {/* Notes */}
            {lead.notes && (
              <div style={{
                marginTop: "10px", padding: "14px 16px", borderRadius: "14px",
                background: "#f8f9fb", border: "1px solid #f1f5f9",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                  <FileText size={14} style={{ color: "#94a3b8" }} />
                  <span style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.04em" }}>Notes</span>
                </div>
                <p style={{ margin: 0, fontSize: "0.92rem", color: "#475569" }}>{getLeadGoal(lead)}</p>
              </div>
            )}

            {/* Action button */}
            <div style={{ marginTop: "24px" }}>
              <motion.button
                onClick={handleOpenChat}
                whileHover={{ scale: 1.02, boxShadow: "0 8px 30px rgba(53,53,243,0.3)" }}
                whileTap={{ scale: 0.97 }}
                style={{
                  display: "inline-flex", alignItems: "center", gap: "8px",
                  padding: "12px 28px", borderRadius: "14px", border: "none",
                  background: "#3535F3", color: "#fff", fontSize: "0.95rem",
                  fontWeight: 600, cursor: "pointer",
                  boxShadow: "0 4px 16px rgba(53,53,243,0.25)",
                }}
              >
                <MessageCircle size={18} />
                Talk to Cleo
              </motion.button>
            </div>
          </div>

          {/* Right column */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px", alignSelf: "start" }}>
            {/* Documents */}
            <DocumentsCard projectId={projectId} ensureProject={ensureProject} />
          </div>
        </motion.div>
      </div>
    </div>
  );
}
