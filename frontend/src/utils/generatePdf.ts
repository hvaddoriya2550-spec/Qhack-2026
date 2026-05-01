import jsPDF from "jspdf";

// Cloover brand — light theme for PDF (matches app)
const INDIGO = "#3535F3";
const INDIGO_LIGHT = "#4747F5";
const PAGE_BG = "#f9fafb";
const CARD_BG = "#ffffff";
const CARD_INNER = "#f8f9fb";
const TEXT_PRIMARY = "#0f172a";
const TEXT_BODY = "#475569";
const TEXT_SECONDARY = "#475569";
const TEXT_MUTED = "#94a3b8";

const PAGE_W = 210; // A4 mm
const PAGE_H = 297;
const MARGIN = 16;
const CONTENT_W = PAGE_W - MARGIN * 2;

interface ReportData {
  customer_summary?: {
    postcode?: string;
    product_interest?: string;
    budget_band?: string;
    customer_goal?: string;
    estimated_profile?: string;
  };
  market_context?: { summary?: string; relevance_signal?: string };
  recommended_packages?: {
    name: string;
    system: string;
    capex: string;
    annual_savings: string;
    fit_reason?: string;
    target_customer?: string;
  }[];
  financing_options?: {
    type: string;
    monthly_payment: string;
    total_cost: string;
    fit_reason?: string;
    recommended?: boolean;
  }[];
  ai_summary?: string;
  best_package?: string;
  best_package_details?: { fit_reason?: string; sales_pitch?: string };
  recommended_financing?: { type?: string; fit_reason?: string };
  installer_pitch?: {
    recommended_opening?: string;
    likely_objection?: string;
    sales_focus?: string;
  };
  credit_assessment?: {
    risk_level?: string;
    co_applicant_needed?: boolean;
    financing_recommendation?: string;
    reasoning?: string;
  };
  confidence?: number;
  assumptions?: string[];
}

function drawGrid(doc: jsPDF) {
  doc.setDrawColor("#eef0f4");
  doc.setLineWidth(0.15);
  for (let x = 0; x <= PAGE_W; x += 10) {
    doc.line(x, 0, x, PAGE_H);
  }
  for (let y = 0; y <= PAGE_H; y += 10) {
    doc.line(0, y, PAGE_W, y);
  }
}

function addPage(doc: jsPDF) {
  doc.addPage();
  doc.setFillColor(PAGE_BG);
  doc.rect(0, 0, PAGE_W, PAGE_H, "F");
  drawGrid(doc);
}

function drawCard(doc: jsPDF, x: number, y: number, w: number, h: number, highlight = false) {
  doc.setFillColor(highlight ? "#f0f0ff" : CARD_BG);
  doc.roundedRect(x, y, w, h, 3, 3, "F");
  doc.setDrawColor(highlight ? INDIGO : "#e5e7eb");
  doc.setLineWidth(highlight ? 0.4 : 0.2);
  doc.roundedRect(x, y, w, h, 3, 3, "S");
}

function wrapText(doc: jsPDF, text: string, maxWidth: number): string[] {
  return doc.splitTextToSize(text, maxWidth);
}

// ── Font helpers for consistent typography ──
function setHeading(doc: jsPDF, size = 16) {
  doc.setFont("helvetica", "bold");
  doc.setFontSize(size);
  doc.setTextColor(TEXT_PRIMARY);
}
function setSubheading(doc: jsPDF, size = 11) {
  doc.setFont("helvetica", "bold");
  doc.setFontSize(size);
  doc.setTextColor(TEXT_PRIMARY);
}
function setBody(doc: jsPDF, size = 9) {
  doc.setFont("helvetica", "normal");
  doc.setFontSize(size);
  doc.setTextColor(TEXT_BODY);
}
function setLabel(doc: jsPDF, size = 7) {
  doc.setFont("helvetica", "normal");
  doc.setFontSize(size);
  doc.setTextColor(TEXT_MUTED);
}
function setAccent(doc: jsPDF, size = 7) {
  doc.setFont("helvetica", "bold");
  doc.setFontSize(size);
  doc.setTextColor(INDIGO);
}
function setValue(doc: jsPDF, size = 12) {
  doc.setFont("helvetica", "bold");
  doc.setFontSize(size);
  doc.setTextColor(TEXT_PRIMARY);
}

export function generateReport(report: ReportData) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });

  // ─── PAGE 1: Cover ───────────────────────────────────────────
  doc.setFillColor(PAGE_BG);
  doc.rect(0, 0, PAGE_W, PAGE_H, "F");
  drawGrid(doc);

  // Accent bar
  doc.setFillColor(INDIGO);
  doc.rect(0, 0, PAGE_W, 4, "F");

  // Logo area
  setHeading(doc, 22);
  doc.text("Cloover", MARGIN, 40);

  setAccent(doc, 10);
  doc.text("AI Sales Coach Report", MARGIN, 48);

  // Title
  setHeading(doc, 24);
  doc.text("Sales Briefing", MARGIN, 75);

  setBody(doc, 11);
  const interest = report.customer_summary?.product_interest || "Energy Solutions";
  doc.text(`${interest} — Personalized Recommendation`, MARGIN, 84);

  // Customer card
  const custY = 100;
  drawCard(doc, MARGIN, custY, CONTENT_W, 58);

  setAccent(doc, 8);
  doc.text("CUSTOMER OVERVIEW", MARGIN + 8, custY + 10);

  setBody(doc, 9);
  const profile = report.customer_summary?.estimated_profile || "—";
  const profileLines = wrapText(doc, profile, CONTENT_W - 16);
  doc.text(profileLines.slice(0, 3), MARGIN + 8, custY + 18);

  setBody(doc, 8);
  const detailPairs = [
    ["Postcode", report.customer_summary?.postcode || "—"],
    ["Interest", report.customer_summary?.product_interest || "—"],
    ["Budget", report.customer_summary?.budget_band || "—"],
  ];
  let dy = custY + 34;
  for (const [lbl, val] of detailPairs) {
    const wrapped = wrapText(doc, `${lbl}: ${val}`, CONTENT_W - 16);
    doc.text(wrapped.slice(0, 1), MARGIN + 8, dy);
    dy += 4;
  }
  const goalText = `Goal: ${report.customer_summary?.customer_goal || "—"}`;
  const goalLines = wrapText(doc, goalText, CONTENT_W - 16);
  doc.text(goalLines.slice(0, 2), MARGIN + 8, dy);

  // AI Summary
  const sumY = 172;
  setBody(doc, 9);
  const sumLines = wrapText(doc, report.ai_summary || "No summary available.", CONTENT_W - 16);
  const sumShown = sumLines.slice(0, 10);
  const sumCardH = 14 + sumShown.length * 4;
  drawCard(doc, MARGIN, sumY, CONTENT_W, sumCardH, true);
  setAccent(doc, 8);
  doc.text("AI SUMMARY", MARGIN + 8, sumY + 10);
  setBody(doc, 9);
  doc.text(sumShown, MARGIN + 8, sumY + 18);

  // Confidence + Best package footer
  const footerY = sumY + sumCardH + 12;
  setLabel(doc, 9);
  doc.text(`Confidence: ${report.confidence ?? 0}/100`, MARGIN, footerY);
  doc.text(`Best Package: ${report.best_package || "—"}`, MARGIN + 80, footerY);
  doc.text(`Generated by Cleo — Cloover AI Sales Coach`, MARGIN, PAGE_H - 12);

  // ─── PAGE 2: Market Context + Packages ───────────────────────
  addPage(doc);
  let y = 16;

  // Accent bar
  doc.setFillColor(INDIGO);
  doc.rect(0, 0, PAGE_W, 3, "F");

  // Market Context
  setHeading(doc, 14);
  doc.text("Market & Regulatory Context", MARGIN, y + 10);
  y += 16;

  setBody(doc, 9);
  const mktLines = wrapText(doc, report.market_context?.summary || "No market data.", CONTENT_W - 16);
  const mktShown = mktLines.slice(0, 12);
  const mktCardH = 20 + mktShown.length * 4;
  drawCard(doc, MARGIN, y, CONTENT_W, mktCardH);
  setLabel(doc, 8);
  const signal = report.market_context?.relevance_signal || "Medium";
  doc.text(`Relevance: ${signal}`, MARGIN + 8, y + 9);
  setBody(doc, 9);
  doc.text(mktShown, MARGIN + 8, y + 17);
  y += mktCardH + 8;

  // Recommended Packages
  setHeading(doc, 14);
  doc.text("Recommended Packages", MARGIN, y);
  y += 8;

  const packages = report.recommended_packages || [];
  const colW = (CONTENT_W - 8) / 3;

  // Package cards side by side
  for (let i = 0; i < Math.min(packages.length, 3); i++) {
    const pkg = packages[i]!;
    const px = MARGIN + i * (colW + 4);
    const isBest = pkg.name === report.best_package;
    drawCard(doc, px, y, colW, 80, isBest);

    let py = y + 8;
    // Name
    setSubheading(doc, 10);
    if (isBest) doc.setTextColor(INDIGO);
    doc.text(pkg.name, px + 6, py);
    if (isBest) {
      py += 4;
      setAccent(doc, 6);
      doc.text("BEST FIT", px + 6, py);
    }
    py += 5;

    // System
    setBody(doc, 7.5);
    const sysLines = wrapText(doc, pkg.system, colW - 12);
    doc.text(sysLines.slice(0, 3), px + 6, py);
    py += sysLines.slice(0, 3).length * 3.2 + 4;

    // Capex
    setLabel(doc, 6.5);
    doc.text("CAPEX", px + 6, py);
    setValue(doc, 11);
    doc.text(`€${Number(pkg.capex).toLocaleString("de-DE")}`, px + 6, py + 5);
    py += 11;

    // Savings
    setLabel(doc, 6.5);
    doc.text("ANNUAL SAVINGS", px + 6, py);
    setAccent(doc, 10);
    doc.text(`€${Number(pkg.annual_savings).toLocaleString("de-DE")}/yr`, px + 6, py + 5);
    py += 10;

    // Fit reason
    if (pkg.fit_reason) {
      setBody(doc, 7);
      const fitLines = wrapText(doc, pkg.fit_reason, colW - 12);
      doc.text(fitLines.slice(0, 2), px + 6, py);
    }
  }

  y += 90;

  // ─── PAGE 3: Financing + Pitch ───────────────────────────────
  if (y > 220) {
    addPage(doc);
    y = 16;
    doc.setFillColor(INDIGO);
    doc.rect(0, 0, PAGE_W, 3, "F");
  }

  // Financing Options
  setHeading(doc, 14);
  doc.text("Financing Options", MARGIN, y);
  y += 8;

  const finOptions = report.financing_options || [];
  for (let i = 0; i < Math.min(finOptions.length, 3); i++) {
    const fin = finOptions[i]!;
    const fx = MARGIN + i * (colW + 4);
    drawCard(doc, fx, y, colW, 50, fin.recommended);

    let fy = y + 8;
    setSubheading(doc, 9);
    if (fin.recommended) doc.setTextColor(INDIGO);
    doc.text(fin.type, fx + 6, fy);
    if (fin.recommended) {
      fy += 4;
      setAccent(doc, 6);
      doc.text("RECOMMENDED", fx + 6, fy);
    }
    fy += 5;

    setLabel(doc, 6.5);
    doc.text("MONTHLY", fx + 6, fy);
    setValue(doc, 11);
    doc.text(`€${fin.monthly_payment}`, fx + 6, fy + 5);
    fy += 10;

    setLabel(doc, 6.5);
    doc.text("TOTAL COST", fx + 6, fy);
    setBody(doc, 9);
    doc.text(`€${Number(fin.total_cost).toLocaleString("de-DE")}`, fx + 6, fy + 5);
  }

  y += 60;

  // Installer Pitch Guidance
  if (y > 240) {
    addPage(doc);
    y = 16;
    doc.setFillColor(INDIGO);
    doc.rect(0, 0, PAGE_W, 3, "F");
  }

  setHeading(doc, 14);
  doc.text("Installer Pitch Guidance", MARGIN, y);
  y += 8;

  const pitchItems = [
    { label: "RECOMMENDED OPENING", value: report.installer_pitch?.recommended_opening },
    { label: "LIKELY OBJECTION", value: report.installer_pitch?.likely_objection },
    { label: "SALES FOCUS", value: report.installer_pitch?.sales_focus },
  ];

  // Calculate dynamic card height
  doc.setFontSize(9);
  let pitchH = 16;
  for (const item of pitchItems) {
    const lines = wrapText(doc, item.value || "—", CONTENT_W - 16);
    pitchH += 4 + lines.slice(0, 4).length * 3.8 + 4;
  }

  drawCard(doc, MARGIN, y, CONTENT_W, pitchH);
  let py = y + 10;

  for (const item of pitchItems) {
    setAccent(doc, 7);
    doc.text(item.label, MARGIN + 8, py);
    py += 4;
    setBody(doc, 8.5);
    const lines = wrapText(doc, item.value || "—", CONTENT_W - 16);
    const shown = lines.slice(0, 4);
    doc.text(shown, MARGIN + 8, py);
    py += shown.length * 3.8 + 4;
  }

  y = py + 6;

  // Best Package Details
  if (report.best_package_details) {
    if (y > 250) {
      addPage(doc);
      y = 16;
      doc.setFillColor(INDIGO);
      doc.rect(0, 0, PAGE_W, 3, "F");
    }

    setBody(doc, 9);
    const spLines = wrapText(doc, report.best_package_details.sales_pitch || "—", CONTENT_W - 16);
    const spShown = spLines.slice(0, 6);
    const spCardH = 20 + spShown.length * 4;
    drawCard(doc, MARGIN, y, CONTENT_W, spCardH, true);
    setAccent(doc, 7);
    doc.text("BEST PACKAGE — SALES PITCH", MARGIN + 8, y + 9);
    setBody(doc, 9);
    doc.text(spShown, MARGIN + 8, y + 16);
    y += spCardH + 4;
  }

  // Credit Assessment
  if (report.credit_assessment) {
    y += 6;
    if (y > 240) {
      addPage(doc);
      y = 16;
      doc.setFillColor(INDIGO);
      doc.rect(0, 0, PAGE_W, 3, "F");
    }
    const ca = report.credit_assessment;
    const riskColor = ca.risk_level === "LOW" ? "#16a34a" : ca.risk_level === "HIGH" ? "#dc2626" : "#d97706";
    drawCard(doc, MARGIN, y, CONTENT_W, 36);
    setAccent(doc, 7);
    doc.text("CREDIT ASSESSMENT — FOR CLOOVER FINANCING TEAM", MARGIN + 8, y + 9);

    setLabel(doc, 7);
    doc.text("Risk Level:", MARGIN + 8, y + 16);
    doc.setTextColor(riskColor);
    doc.setFont("helvetica", "bold");
    doc.text(ca.risk_level || "MEDIUM", MARGIN + 30, y + 16);

    setLabel(doc, 7);
    doc.text("Co-applicant:", MARGIN + 60, y + 16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(TEXT_PRIMARY);
    doc.text(ca.co_applicant_needed ? "Yes" : "No", MARGIN + 85, y + 16);

    setLabel(doc, 7);
    doc.text("Recommendation:", MARGIN + 100, y + 16);
    const recColor = ca.financing_recommendation === "Yes" ? "#16a34a" : ca.financing_recommendation === "Review needed" ? "#dc2626" : "#d97706";
    doc.setTextColor(recColor);
    doc.setFont("helvetica", "bold");
    doc.text(ca.financing_recommendation || "Review needed", MARGIN + 130, y + 16);

    if (ca.reasoning) {
      setBody(doc, 8);
      const reasonLines = wrapText(doc, ca.reasoning, CONTENT_W - 16);
      doc.text(reasonLines.slice(0, 2), MARGIN + 8, y + 24);
    }
    y += 40;
  }

  // Assumptions on last page
  if (report.assumptions?.length) {
    y += 45;
    if (y > 240) {
      addPage(doc);
      y = 16;
      doc.setFillColor(INDIGO);
      doc.rect(0, 0, PAGE_W, 3, "F");
    }
    setLabel(doc, 9);
    doc.text("Assumptions:", MARGIN, y);
    y += 6;
    setBody(doc, 7.5);
    for (const a of report.assumptions.slice(0, 6)) {
      const lines = wrapText(doc, `• ${a}`, CONTENT_W - 8);
      for (const line of lines) {
        if (y > PAGE_H - 20) {
          addPage(doc);
          y = 16;
        }
        doc.text(line, MARGIN + 4, y);
        y += 3.5;
      }
      y += 1;
    }
  }

  // Footer on last page
  setLabel(doc, 8);
  doc.text("Generated by Cleo — Cloover AI Sales Coach", MARGIN, PAGE_H - 10);
  doc.text(new Date().toLocaleDateString("de-DE"), PAGE_W - MARGIN - 25, PAGE_H - 10);

  // Save
  const name = report.customer_summary?.postcode || "report";
  doc.save(`Cloover_Sales_Report_${name}.pdf`);
}
