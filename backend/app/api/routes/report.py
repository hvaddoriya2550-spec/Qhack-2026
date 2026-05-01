import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sales.schemas import SalesData, SalesPhase
from app.core.config import settings
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.project import Project

router = APIRouter()

REPORT_SYSTEM_PROMPT = """\
You are a sales report generator for a German residential energy installer.
Given customer data, research findings, and strategy notes, produce a
structured JSON sales briefing.

## German Market Reference Data (use for realistic estimates)

**Product pricing (installed, before subsidies):**
- Solar PV: €1,200–1,400 per kWp (typical systems: 5–15 kWp)
- Battery storage: €500–800 per kWh (typical: 5–15 kWh)
- Heat pump (air-water): €15,000–30,000 fully installed
- Wallbox (EV charger): €800–2,500 installed
- Energy management system: €500–1,500

**Current subsidies & incentives (2025/2026):**
- KfW 270: Low-interest loans for solar + battery (1.5–3.5% APR, up to 20 years)
- BAFA/BEG: Up to 70% subsidy on heat pumps (base 30% + bonuses for replacing old systems)
- §35c EStG: 20% tax deduction for energy renovations over 3 years
- Regional programs vary by Bundesland and municipality
- Carbon price: rising CO₂ tax makes fossil heating more expensive each year

**Electricity prices:** ~€0.35–0.40/kWh (household), feed-in tariff ~€0.08/kWh
**Gas prices:** ~€0.10–0.14/kWh

**Regulations:**
- GEG (Gebäudeenergiegesetz): New/replacement heating must use ≥65% renewables from 2024
- Municipal heat planning deadlines: large cities by mid-2026, smaller by mid-2028

## Instructions

Generate EXACTLY this JSON structure. Use realistic numbers based on the
customer's data and the reference prices above. All monetary values should
be strings (numbers without currency symbol). Output ONLY valid JSON, no
markdown fences, no explanatory text.

{
  "customer_summary": {
    "postcode": "<from data>",
    "product_interest": "<from data>",
    "budget_band": "<from financial_profile or infer>",
    "customer_goal": "<from notes or infer>",
    "estimated_profile": "<1-2 sentence customer profile>"
  },
  "market_context": {
    "summary": "<3-5 sentences on market trends, regulations, energy prices relevant to this customer>",
    "relevance_signal": "<High|Medium|Low>"
  },
  "recommended_packages": [
    {
      "name": "Starter",
      "system": "<specific product combo>",
      "capex": "<total cost before subsidies>",
      "annual_savings": "<estimated annual €>",
      "fit_reason": "<why this tier fits>",
      "target_customer": "<who this is for>"
    },
    {
      "name": "Recommended",
      "system": "<specific product combo>",
      "capex": "<total cost>",
      "annual_savings": "<estimated annual €>",
      "fit_reason": "<why this is the best fit>",
      "target_customer": "<who this is for>"
    },
    {
      "name": "Full Independence",
      "system": "<specific product combo>",
      "capex": "<total cost>",
      "annual_savings": "<estimated annual €>",
      "fit_reason": "<why this maximizes value>",
      "target_customer": "<who this is for>"
    }
  ],
  "financing_options": [
    {
      "type": "Cash Purchase",
      "monthly_payment": "0",
      "total_cost": "<recommended package capex minus subsidies>",
      "fit_reason": "<why cash works>",
      "recommended": false
    },
    {
      "type": "KfW Loan + Subsidy",
      "monthly_payment": "<realistic monthly>",
      "total_cost": "<total over loan term>",
      "fit_reason": "<why this combo works>",
      "recommended": true
    },
    {
      "type": "Full Financing",
      "monthly_payment": "<realistic monthly>",
      "total_cost": "<total over loan term>",
      "fit_reason": "<why full finance>",
      "recommended": false
    }
  ],
  "ai_summary": "<3-4 sentence executive summary of the entire recommendation>",
  "best_package": "Recommended",
  "best_package_details": {
    "fit_reason": "<detailed reason why this package is best for this customer>",
    "sales_pitch": "<2-3 sentence pitch the installer can use verbatim>"
  },
  "recommended_financing": {
    "type": "<name of best financing option>",
    "fit_reason": "<why this financing path is best>"
  },
  "installer_pitch": {
    "recommended_opening": "<first thing the installer should say>",
    "likely_objection": "<most likely customer objection and how to handle it>",
    "sales_focus": "<what to emphasize in the conversation>"
  },
  "credit_assessment": {
    "risk_level": "<LOW|MEDIUM|HIGH>",
    "co_applicant_needed": <true|false>,
    "financing_recommendation": "<Yes|Yes with conditions|Review needed>",
    "reasoning": "<1-2 sentences explaining the assessment based on available data>"
  },
  "confidence": <0-100 integer>,
  "assumptions": ["<list of assumptions made due to missing data>"]
}
"""


def _build_sales_data_from_project(project: Project) -> SalesData:
    """Build SalesData from a Project row (mirrors chat_service logic)."""
    sd = SalesData(
        customer_name=project.customer_name,
        postal_code=project.postal_code,
        city=project.city,
        product_interest=project.product_interest,
        household_size=project.household_size,
        house_type=project.house_type,
        build_year=project.build_year,
        roof_orientation=project.roof_orientation,
        electricity_kwh_year=project.electricity_kwh_year,
        heating_type=project.heating_type,
        monthly_energy_bill_eur=project.monthly_energy_bill_eur,
        existing_assets=project.existing_assets,
        financial_profile=project.financial_profile,
        notes=project.notes,
        recommendations=project.recommendations or [],
        competitors=project.competitors or [],
    )

    rd = project.research_data or {}
    sd.market_trends = rd.get("market_trends", [])
    sd.regional_incentives = rd.get("regional_incentives", [])
    sd.energy_price_outlook = rd.get("energy_price_outlook")
    sd.industry_insights = rd.get("industry_insights", [])

    sn = project.strategy_notes or {}
    sd.positioning = sn.get("positioning")
    sd.value_proposition = sn.get("value_proposition")
    sd.key_messages = sn.get("key_messages", [])
    sd.objections = sn.get("objections", [])
    sd.savings_estimate = sn.get("savings_estimate")
    sd.payback_period = sn.get("payback_period")
    sd.financing_options = sn.get("financing_options", [])

    phase_map = {
        "data_gathering": SalesPhase.DATA_GATHERING,
        "research": SalesPhase.RESEARCH,
        "strategy": SalesPhase.STRATEGY,
        "deliverable": SalesPhase.DELIVERABLE,
        "complete": SalesPhase.COMPLETE,
    }
    sd.phase = phase_map.get(
        project.status or "data_gathering", SalesPhase.DATA_GATHERING
    )

    return sd


def _compute_confidence(sd: SalesData) -> int:
    """Dynamic confidence score based on data completeness and quality."""
    score = 0

    # Customer data (max 30 points)
    customer_fields = [
        sd.customer_name, sd.postal_code, sd.city, sd.product_interest,
        sd.household_size, sd.house_type, sd.build_year, sd.roof_orientation,
        sd.electricity_kwh_year, sd.heating_type, sd.monthly_energy_bill_eur,
        sd.existing_assets, sd.financial_profile, sd.notes,
    ]
    filled = sum(1 for f in customer_fields if f is not None)
    score += int(filled / len(customer_fields) * 30)

    # Research quality (max 25 points)
    if sd.regional_incentives:
        score += min(len(sd.regional_incentives) * 4, 12)
    if sd.energy_price_outlook:
        score += 5
    if sd.market_trends:
        score += min(len(sd.market_trends) * 3, 8)

    # Strategy quality (max 25 points)
    if sd.value_proposition:
        score += 8
    if sd.key_messages:
        score += min(len(sd.key_messages) * 2, 8)
    if sd.savings_estimate:
        score += 5
    if sd.financing_options:
        score += 4

    # Extras (max 20 points)
    if sd.competitors:
        score += min(len(sd.competitors) * 3, 6)
    if sd.objections:
        score += min(len(sd.objections) * 2, 6)
    if sd.payback_period:
        score += 4
    if sd.positioning:
        score += 4

    return min(score, 100)


@router.post("/generate/{project_id}")
async def generate_report(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a structured sales report for a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    sd = _build_sales_data_from_project(project)
    confidence = _compute_confidence(sd)

    # Build context for the LLM
    data_dump = sd.model_dump(exclude_none=True, exclude_defaults=True)
    data_dump.pop("phase", None)

    # Load full conversation history for this project
    chat_history = ""
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    conv = conv_result.scalar_one_or_none()
    if conv:
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        )
        messages = msg_result.scalars().all()
        chat_lines = []
        for msg in messages:
            role = msg.role.upper()
            agent = f" ({msg.agent_name})" if msg.agent_name else ""
            chat_lines.append(f"[{role}{agent}]: {msg.content}")
        chat_history = "\n\n".join(chat_lines)

    user_prompt = (
        f"Generate a sales report for this customer.\n\n"
        f"Customer & research data:\n{json.dumps(data_dump, indent=2, default=str)}\n\n"
    )
    if chat_history:
        user_prompt += (
            f"Full conversation history between the AI Sales Coach and the installer:\n"
            f"---\n{chat_history}\n---\n\n"
            f"Use the conversation above to extract all research findings, strategy "
            f"decisions, objections discussed, and any installer preferences.\n\n"
        )
    user_prompt += (
        f"Confidence level: {confidence}/100\n"
        f"Set the confidence field to {confidence}."
    )

    # Use Gemini directly with response_mime_type for guaranteed JSON
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    config = genai_types.GenerateContentConfig(
        system_instruction=REPORT_SYSTEM_PROMPT,
        max_output_tokens=16384,
        response_mime_type="application/json",
    )

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=user_prompt)],
            )],
            config=config,
        )
        report = json.loads(response.text.strip())
    except (json.JSONDecodeError, Exception) as e:
        raise HTTPException(
            status_code=502,
            detail=f"Report generation failed: {e}",
        )

    # Ensure confidence is set
    report["confidence"] = confidence

    return report
