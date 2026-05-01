"""FinancialAgent — deterministic financing pipeline (Pillar 2 of the brief).

Consumes the tiered bundles from AnalysisAgent and produces, for each tier:

  * Subsidy breakdown (KfW 270 loans, BEG/BAFA heat pump grants, KfW 458)
  * Three financing scenarios (Cash / Subsidy + Cash / Subsidy + Financing)
  * 10- and 20-year cumulative savings with energy-price escalation
  * Age-based suitability alert (green / yellow / red) per scenario
  * Recommended scenario for this specific customer

The numbers are deterministic Python — no LLM math. One Gemini call at the
end generates an affordability narrative grounded in those numbers so the
sales rep has something quotable for the customer meeting.

Disclaimer: this is a sales-coach tool, not an underwriting engine. Age
flags are "review recommended" alerts, never automatic declines.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.agents.base.agent import BaseAgent
from app.agents.base.llm import chat_completion
from app.agents.base.types import AgentContext, AgentMessage, MessageRole
from app.agents.sales.schemas import (
    BundleTier,
    FinancingScenario,
    SalesData,
    SalesPhase,
    SubsidyLine,
)
from app.core.logging import logger

# ── calibration constants ───────────────────────────────────────────

# Annual retail energy price escalation used for 10/20-year projections.
# Germany has averaged ~3-4%/yr on residential electricity. Conservative.
PRICE_ESCALATION_PCT = 3.0

# Rough self-consumption rates for solar energy (how much of the solar
# the household actually uses vs. exports to the grid).
SELF_CONSUMPTION_NO_BATTERY = 0.30
SELF_CONSUMPTION_WITH_BATTERY = 0.65

# Current EEG feed-in tariff for residential solar ≤ 10 kWp (ct/kWh).
# As of 2025 the partial feed-in rate is ~8.03 ct/kWh for systems ≤ 10 kWp.
FEED_IN_TARIFF_EUR_KWH = 0.0803

# Fraction of heating cost that a heat pump saves when replacing
# oil/gas/district in a typical existing German home. Conservative.
HEAT_PUMP_HEATING_SAVINGS_FRACTION = 0.50

# Age-suitability age bands (in years at end of loan term).
AGE_GREEN_MAX_END = 75  # loan ends before ~75 → green
AGE_YELLOW_MAX_END = 85  # 76..85 → yellow (review); 86+ → red


# ── KfW / BAFA / BEG subsidy rulebook (hackathon MVP) ───────────────
# These are simplified demo rules — in production you'd hit the real
# KfW/BAFA/BEG rulebooks with income tests, property registers, etc.

# KfW 270 "Erneuerbare Energien – Standard": low-interest loan for
# solar PV + battery. Current effective rate ~4.7% (Nov 2025), up to 20y.
KFW_270_RATE_PCT = 4.70
KFW_270_MAX_YEARS = 20

# KfW 458 "Heat pump loan" — pairs with BEG grant, ~3.5% up to 10y.
KFW_458_RATE_PCT = 3.50
KFW_458_MAX_YEARS = 10

# BEG EM (Bundesförderung für effiziente Gebäude — Einzelmaßnahmen):
# GRANT for heat pump replacement.
#   Base rate: 30%
#   Climate speed bonus (replacing old oil/gas/coal before deadline): +20%
#   Income bonus (household < €40k): +30% (we only apply if profile hints low income)
#   Max total: 70%
# Eligible cost cap: €30,000 per residential unit → max grant €21,000.
BEG_HEATPUMP_BASE_PCT = 30.0
BEG_HEATPUMP_SPEED_BONUS_PCT = 20.0
BEG_HEATPUMP_INCOME_BONUS_PCT = 30.0
BEG_HEATPUMP_MAX_PCT = 70.0
BEG_HEATPUMP_ELIGIBLE_CAP_EUR = 30_000


# ── component detection helpers ─────────────────────────────────────


def _contains(text: str | None, *keywords: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in keywords)


def _is_solar(item_name: str) -> bool:
    return _contains(item_name, "solar", "pv", "photovolta")


def _is_battery(item_name: str) -> bool:
    return _contains(item_name, "batter", "storage", "speicher")


def _is_heat_pump(item_name: str) -> bool:
    return _contains(item_name, "heat pump", "heatpump", "wärmepumpe", "waermepumpe")


def _is_wallbox(item_name: str) -> bool:
    return _contains(item_name, "wallbox", "ev charg", "ladesta")


def _parse_price(price_str: str) -> int:
    """Best-effort midpoint from a range like '€8,000–€12,000'."""
    if not price_str:
        return 0
    digits = []
    current = ""
    for ch in price_str:
        if ch.isdigit():
            current += ch
        elif current:
            digits.append(int(current))
            current = ""
    if current:
        digits.append(int(current))
    if not digits:
        return 0
    if len(digits) == 1:
        return digits[0]
    return sum(digits) // len(digits)


def _tier_component_costs(tier: BundleTier) -> dict[str, int]:
    """Break a tier's total cost into buckets per component type."""
    buckets: dict[str, int] = {
        "solar": 0,
        "battery": 0,
        "heat_pump": 0,
        "wallbox": 0,
        "other": 0,
    }
    total_from_items = 0
    for item in tier.items:
        cost = _parse_price(item.estimated_price_eur)
        total_from_items += cost
        name = item.name
        if _is_heat_pump(name):
            buckets["heat_pump"] += cost
        elif _is_battery(name):
            buckets["battery"] += cost
        elif _is_solar(name):
            buckets["solar"] += cost
        elif _is_wallbox(name):
            buckets["wallbox"] += cost
        else:
            buckets["other"] += cost

    # If item prices don't add up to the tier's upfront_cost_eur, scale
    # the buckets proportionally so the totals match.
    if tier.upfront_cost_eur and total_from_items > 0:
        scale = tier.upfront_cost_eur / total_from_items
        buckets = {k: int(round(v * scale)) for k, v in buckets.items()}
        # Fix any rounding drift
        drift = tier.upfront_cost_eur - sum(buckets.values())
        if drift:
            buckets["other"] += drift

    return buckets


# ── deterministic calculators ───────────────────────────────────────


def loan_payment(principal: float, apr_pct: float, term_years: int) -> float:
    """Monthly payment for a fully-amortized loan."""
    if principal <= 0 or term_years <= 0:
        return 0.0
    if apr_pct <= 0:
        return principal / (term_years * 12)
    r = apr_pct / 100.0 / 12.0
    n = term_years * 12
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def cumulative_energy_savings(
    annual_savings_eur: float, years: int, escalation_pct: float = PRICE_ESCALATION_PCT
) -> float:
    """Sum of escalating annual savings over N years.

    Uses a simple year-by-year compound since closed form is cosmetic
    for this scale. Represents the fact that as energy prices rise,
    the value of the savings grows too.
    """
    if annual_savings_eur <= 0 or years <= 0:
        return 0.0
    total = 0.0
    g = 1.0 + (escalation_pct / 100.0)
    for i in range(years):
        total += annual_savings_eur * (g ** i)
    return total


def assess_age_suitability(
    age: int | None, term_years: int | None
) -> tuple[str, list[str], list[str]]:
    """Return (tier, alerts, alternative_paths).

    Never a hard decline — this is a sales-coach risk flag only.
    """
    if age is None or term_years is None or term_years <= 0:
        return "green", [], []
    end_age = age + term_years
    if end_age <= AGE_GREEN_MAX_END:
        return "green", [], []
    if end_age <= AGE_YELLOW_MAX_END:
        return (
            "yellow",
            [
                f"Review financing suitability: age {age} + {term_years}-year term "
                f"→ repayment extends to age {end_age}."
            ],
            ["Shorter loan term", "Higher upfront payment", "Co-borrower application"],
        )
    return (
        "red",
        [
            f"Strong mismatch: age {age} with {term_years}-year term "
            f"(ends at age {end_age}).",
            "Avoid leading with this scenario. Discuss shorter tenor first.",
        ],
        [
            "Shorter loan term (≤ 10 years)",
            "Higher upfront payment",
            "Co-borrower application",
            "Guarantor-supported application",
            "Smaller starter package",
        ],
    )


# ── subsidy logic ───────────────────────────────────────────────────


def _detect_low_income(financial_profile: str | None) -> bool:
    return _contains(
        financial_profile,
        "low income",
        "limited upfront",
        "financing required",
        "budget constrained",
    )


def _detect_replacing_fossil_heating(heating_type: str | None) -> bool:
    """Climate speed bonus applies when replacing oil/gas/coal heating."""
    return _contains(heating_type, "oil", "gas", "coal", "öl")


def compute_subsidies(
    buckets: dict[str, int],
    *,
    heating_type: str | None,
    financial_profile: str | None,
    existing_assets: str | None,
) -> list[SubsidyLine]:
    """Apply the hard-coded rulebook to a single tier's component buckets.

    Returns SubsidyLine entries (mix of grants and loans).
    """
    lines: list[SubsidyLine] = []

    # ── Heat pump: BEG EM grant + optional KfW 458 for the remainder ──
    hp_cost = buckets.get("heat_pump", 0)
    if hp_cost > 0:
        rate = BEG_HEATPUMP_BASE_PCT
        reasons = ["base 30%"]
        if _detect_replacing_fossil_heating(heating_type):
            rate += BEG_HEATPUMP_SPEED_BONUS_PCT
            reasons.append("+20% climate speed bonus (replacing fossil heating)")
        if _detect_low_income(financial_profile):
            rate += BEG_HEATPUMP_INCOME_BONUS_PCT
            reasons.append("+30% income bonus")
        rate = min(rate, BEG_HEATPUMP_MAX_PCT)
        eligible = min(hp_cost, BEG_HEATPUMP_ELIGIBLE_CAP_EUR)
        grant = int(round(eligible * (rate / 100.0)))
        lines.append(
            SubsidyLine(
                program="BEG EM / BAFA Heizungsförderung",
                component="Heat pump",
                kind="grant",
                amount_eur=grant,
                eligibility_notes=(
                    f"{rate:.0f}% on eligible €{eligible:,} ({', '.join(reasons)})."
                ),
            )
        )
        # Remaining HP cost can be financed via KfW 458
        remaining_hp = hp_cost - grant
        if remaining_hp > 0:
            lines.append(
                SubsidyLine(
                    program="KfW 458 Heizungskredit",
                    component="Heat pump",
                    kind="loan",
                    amount_eur=remaining_hp,
                    interest_rate_pct=KFW_458_RATE_PCT,
                    max_term_years=KFW_458_MAX_YEARS,
                    eligibility_notes=(
                        "Low-interest loan for the post-grant remainder. "
                        "Pairs with BEG EM grant."
                    ),
                )
            )

    # ── Solar + Battery: KfW 270 loan ───────────────────────────────
    solar_cost = buckets.get("solar", 0)
    battery_cost = buckets.get("battery", 0)
    pv_package = solar_cost + battery_cost
    if pv_package > 0:
        lines.append(
            SubsidyLine(
                program="KfW 270 Erneuerbare Energien – Standard",
                component="Solar PV + Battery" if battery_cost else "Solar PV",
                kind="loan",
                amount_eur=pv_package,
                interest_rate_pct=KFW_270_RATE_PCT,
                max_term_years=KFW_270_MAX_YEARS,
                eligibility_notes=(
                    "Covers up to 100% of eligible cost for new solar/battery "
                    "installations."
                ),
            )
        )

    # Wallbox currently has no federal grant (KfW 440 closed in 2022).
    # We note it transparently instead of pretending otherwise.
    wallbox_cost = buckets.get("wallbox", 0)
    if wallbox_cost > 0:
        lines.append(
            SubsidyLine(
                program="(no federal grant)",
                component="Wallbox",
                kind="grant",
                amount_eur=0,
                eligibility_notes=(
                    "KfW 440 wallbox grant closed in 2022. Check local "
                    "municipal or regional programs for residual funding."
                ),
            )
        )

    return lines


# ── scenario builder ────────────────────────────────────────────────


def _total_grants(lines: list[SubsidyLine]) -> int:
    return sum(line.amount_eur for line in lines if line.kind == "grant")


def _loan_terms(lines: list[SubsidyLine]) -> tuple[int, float, int]:
    """Pick the dominant loan (largest principal) to represent the package.

    Returns (principal_eur, apr_pct, term_years). If no loans, returns zeros.
    """
    loans = [l for l in lines if l.kind == "loan" and l.amount_eur > 0]
    if not loans:
        return 0, 0.0, 0
    dominant = max(loans, key=lambda l: l.amount_eur)
    total_principal = sum(l.amount_eur for l in loans)
    # Use the dominant loan's rate/term as the representative terms.
    return (
        total_principal,
        dominant.interest_rate_pct or 0.0,
        dominant.max_term_years or 0,
    )


def build_scenarios_for_tier(
    tier: BundleTier,
    subsidy_lines: list[SubsidyLine],
    *,
    customer_age: int | None,
) -> list[FinancingScenario]:
    """Three payment paths: Cash, Subsidy + Cash, Subsidy + Financing."""
    grants = _total_grants(subsidy_lines)
    principal, apr, term = _loan_terms(subsidy_lines)

    # Annual savings from the tier (already LLM-estimated).
    annual = float(tier.annual_savings_eur)

    scenarios: list[FinancingScenario] = []

    # ── 1) Cash (no subsidies, no loan) ─────────────────────────────
    cash_upfront = tier.upfront_cost_eur
    cash_total_10y = int(cumulative_energy_savings(annual, 10) - cash_upfront)
    cash_total_20y = int(cumulative_energy_savings(annual, 20) - cash_upfront)
    scenarios.append(
        FinancingScenario(
            tier_name=tier.name,
            name="Cash (full upfront)",
            upfront_eur=cash_upfront,
            financed_eur=0,
            monthly_payment_eur=0,
            interest_rate_pct=None,
            term_years=None,
            total_cost_eur=cash_upfront,
            total_savings_10y_eur=cash_total_10y,
            total_savings_20y_eur=cash_total_20y,
            age_suitability_tier="green",
            age_alerts=[],
            narrative=(
                f"Pay the full €{cash_upfront:,} upfront. Fastest path to "
                f"payback; no interest cost. Ignores subsidies."
            ),
        )
    )

    # ── 2) Subsidy + Cash (apply grants, pay the rest cash) ─────────
    # Net out-of-pocket = tier cost − grants. No loan, no interest.
    net_after_grants = max(0, cash_upfront - grants)
    subsidy_cash_total_10y = int(cumulative_energy_savings(annual, 10) - net_after_grants)
    subsidy_cash_total_20y = int(cumulative_energy_savings(annual, 20) - net_after_grants)
    scenarios.append(
        FinancingScenario(
            tier_name=tier.name,
            name="Subsidy + Cash",
            upfront_eur=net_after_grants,
            financed_eur=0,
            monthly_payment_eur=0,
            interest_rate_pct=None,
            term_years=None,
            total_cost_eur=net_after_grants,
            total_savings_10y_eur=subsidy_cash_total_10y,
            total_savings_20y_eur=subsidy_cash_total_20y,
            age_suitability_tier="green",
            age_alerts=[],
            narrative=(
                f"Apply €{grants:,} in grants, then pay the remaining "
                f"€{net_after_grants:,} cash. No interest, no monthly burden."
            ),
        )
    )

    # ── 3) Subsidy + Financing (grants + KfW loan on the rest) ──────
    if principal > 0 and apr > 0 and term > 0:
        monthly = loan_payment(principal, apr, term)
        total_paid_over_loan = monthly * term * 12
        # Customer upfront day 1 under this path: non-financed + non-granted piece
        non_financed = max(0, cash_upfront - grants - principal)
        total_out_of_pocket = non_financed + total_paid_over_loan

        # Cumulative savings over the loan term and beyond
        savings_10y = cumulative_energy_savings(annual, 10)
        savings_20y = cumulative_energy_savings(annual, 20)
        # Payments during 10y: min(10, term) years of monthly payments
        payments_10y = monthly * 12 * min(10, term)
        payments_20y = monthly * 12 * min(20, term)
        # Include the non-financed upfront once
        net_10y = int(savings_10y - payments_10y - non_financed)
        net_20y = int(savings_20y - payments_20y - non_financed)

        suit_tier, alerts, _paths = assess_age_suitability(customer_age, term)

        scenarios.append(
            FinancingScenario(
                tier_name=tier.name,
                name=f"Subsidy + KfW financing ({term}y @ {apr:.1f}%)",
                upfront_eur=non_financed,
                financed_eur=principal,
                monthly_payment_eur=int(round(monthly)),
                interest_rate_pct=apr,
                term_years=term,
                total_cost_eur=int(round(non_financed + total_paid_over_loan)),
                total_savings_10y_eur=net_10y,
                total_savings_20y_eur=net_20y,
                age_suitability_tier=suit_tier,
                age_alerts=alerts,
                narrative=(
                    f"Apply €{grants:,} in grants, finance €{principal:,} "
                    f"via KfW at {apr:.1f}% over {term} years "
                    f"(~€{int(round(monthly)):,}/month). "
                    f"Day-1 out-of-pocket: €{non_financed:,}."
                ),
            )
        )
    return scenarios


# ── main agent ──────────────────────────────────────────────────────


def _get_sales_data(context: AgentContext) -> SalesData:
    raw = context.shared_state.get("sales_data")
    if isinstance(raw, SalesData):
        return raw
    if isinstance(raw, dict):
        return SalesData(**raw)
    return SalesData()


def _save_sales_data(context: AgentContext, data: SalesData) -> None:
    context.shared_state["sales_data"] = data.model_dump()


def _pick_recommended_scenario(
    scenarios: list[FinancingScenario],
    *,
    financial_profile: str | None,
    age: int | None,
) -> FinancingScenario | None:
    """Heuristic: prefer Recommended tier + the best age-safe scenario."""
    if not scenarios:
        return None
    # Prefer scenarios from the "Recommended" tier
    preferred = [s for s in scenarios if s.tier_name.lower() == "recommended"]
    pool = preferred or scenarios
    # Drop red scenarios entirely
    safe = [s for s in pool if s.age_suitability_tier != "red"] or pool
    # Prefer Subsidy + Cash if customer has cash, otherwise Subsidy + Financing
    if _contains(financial_profile, "cash", "high income", "investor"):
        for s in safe:
            if "Subsidy + Cash" in s.name:
                return s
    for s in safe:
        if "Subsidy + KfW" in s.name:
            return s
    return safe[0]


def _build_summary(data: SalesData) -> str:
    lines = ["## Financial scenarios"]

    if data.subsidy_breakdown:
        lines.append("\n### Applied subsidies")
        for line in data.subsidy_breakdown:
            kind_tag = "💶 Grant" if line.kind == "grant" else "💳 Loan"
            extra = ""
            if line.kind == "loan" and line.interest_rate_pct is not None:
                extra = f" @ {line.interest_rate_pct:.1f}% up to {line.max_term_years}y"
            lines.append(
                f"- **{line.program}** — {line.component}: "
                f"{kind_tag} €{line.amount_eur:,}{extra}"
            )
            if line.eligibility_notes:
                lines.append(f"  > {line.eligibility_notes}")

    if data.financing_scenarios:
        lines.append("\n### Scenarios per tier")
        current_tier = None
        for s in data.financing_scenarios:
            if s.tier_name != current_tier:
                current_tier = s.tier_name
                lines.append(f"\n**{current_tier}:**")
            tag = ""
            if s.age_suitability_tier == "yellow":
                tag = " ⚠️"
            elif s.age_suitability_tier == "red":
                tag = " 🛑"
            lines.append(
                f"- {s.name}{tag}: upfront €{s.upfront_eur:,}"
                + (f", €{s.monthly_payment_eur:,}/mo" if s.monthly_payment_eur else "")
                + f" • 10y net €{s.total_savings_10y_eur:,}"
                + f" • 20y net €{s.total_savings_20y_eur:,}"
            )
            for alert in s.age_alerts:
                lines.append(f"  > {alert}")

    if data.recommended_scenario_tier and data.recommended_scenario_name:
        lines.append(
            f"\n**Recommended for this customer:** "
            f"{data.recommended_scenario_tier} — {data.recommended_scenario_name}"
        )

    if data.affordability_narrative:
        lines.append(f"\n### Affordability\n{data.affordability_narrative}")

    if data.financing_risk_alerts:
        lines.append("\n### Risk alerts")
        for a in data.financing_risk_alerts:
            lines.append(f"- {a}")

    lines.append("\nReady for the strategy phase.")
    return "\n".join(lines)


NARRATIVE_SYSTEM = """\
You are a sales coach writing an affordability and credit risk briefing for \
an energy installer sales rep. You receive structured financing scenarios \
the rep can propose to the customer. Your job is to:

1. Name the scenario that best fits the customer's profile and age.
2. Explain in plain language why it fits (cash position, age-based risk, \
   total savings).
3. Warn the rep about any age-based risk flags that are yellow or red.
4. Provide a **Credit Risk Assessment** based on available data:
   - Infer creditworthiness from: financial_profile, age, household_size, \
     house ownership (detached house = likely owner = positive signal), \
     monthly energy bill (proxy for disposable income), existing_assets.
   - Rate the financing risk as: LOW / MEDIUM / HIGH
   - Flag if a co-applicant might be needed (e.g. single income, older \
     customer with long loan term, limited budget profile).
   - Note: we don't have SCHUFA data — this is an intelligent estimate \
     for the installer to flag with Cloover's financing team.
5. State a clear **Financing Recommendation**: should Cloover offer \
   financing to this customer? (Yes / Yes with conditions / Review needed)

Be concise, grounded, and practical. No marketing fluff."""


NARRATIVE_TOOL = {
    "name": "store_affordability_narrative",
    "description": "Store the affordability briefing with credit risk assessment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "narrative": {"type": "string"},
            "credit_risk": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH"],
                "description": "Inferred credit risk level",
            },
            "co_applicant_flag": {
                "type": "boolean",
                "description": "True if a co-applicant might be needed",
            },
            "financing_recommendation": {
                "type": "string",
                "enum": ["Yes", "Yes with conditions", "Review needed"],
                "description": "Should Cloover offer financing?",
            },
        },
        "required": ["narrative", "credit_risk", "financing_recommendation"],
    },
}


@dataclass
class FinancialAgent(BaseAgent):
    name: str = "financial"
    description: str = (
        "Turns bundle tiers into structured financing scenarios "
        "with subsidies, loan math, and age-based suitability alerts."
    )
    system_prompt: str = ""

    async def execute(
        self, context: AgentContext, message: AgentMessage
    ) -> AgentMessage:
        sales_data = _get_sales_data(context)

        tiers = sales_data.bundle_tiers
        if not tiers and sales_data.optimal_bundle:
            # Fall back: wrap the legacy optimal_bundle as a single "Recommended" tier.
            tiers = [
                BundleTier(
                    name="Recommended",
                    items=sales_data.optimal_bundle,
                    upfront_cost_eur=sales_data.optimal_bundle_total_cost_eur or 0,
                    annual_savings_eur=0,
                    narrative=sales_data.optimal_bundle_rationale or "",
                )
            ]

        if not tiers:
            logger.warning("FinancialAgent: no bundle tiers available")
            return AgentMessage(
                role=MessageRole.ASSISTANT,
                content=(
                    "Cannot run financial analysis: no bundle tiers are "
                    "available. Run the analysis phase first."
                ),
                agent_name=self.name,
                metadata={"phase": sales_data.phase.value},
            )

        customer_age = sales_data.age

        # Build subsidies + scenarios tier by tier.
        all_subsidies: list[SubsidyLine] = []
        all_scenarios: list[FinancingScenario] = []
        seen_subsidy_keys: set[tuple[str, str, int]] = set()
        for tier in tiers:
            buckets = _tier_component_costs(tier)
            subsidies = compute_subsidies(
                buckets,
                heating_type=sales_data.heating_type,
                financial_profile=sales_data.financial_profile,
                existing_assets=sales_data.existing_assets,
            )
            # Dedupe subsidy lines across tiers (they repeat for obvious reasons).
            for line in subsidies:
                key = (line.program, line.component, line.amount_eur)
                if key not in seen_subsidy_keys:
                    seen_subsidy_keys.add(key)
                    all_subsidies.append(line)

            scenarios = build_scenarios_for_tier(
                tier, subsidies, customer_age=customer_age
            )
            all_scenarios.extend(scenarios)

        sales_data.subsidy_breakdown = all_subsidies
        sales_data.financing_scenarios = all_scenarios

        # Effective out-of-pocket = best subsidy-aware upfront across tiers.
        subsidy_cash_scenarios = [
            s for s in all_scenarios if "Subsidy + Cash" in s.name
        ]
        if subsidy_cash_scenarios:
            sales_data.effective_out_of_pocket_eur = min(
                s.upfront_eur for s in subsidy_cash_scenarios
            )

        # Roll up age-based risk alerts at the customer level
        risk_alerts: list[str] = []
        worst_tier = "green"
        alt_paths: list[str] = []
        for s in all_scenarios:
            if s.age_suitability_tier == "red":
                worst_tier = "red"
                risk_alerts.extend(s.age_alerts)
            elif s.age_suitability_tier == "yellow" and worst_tier != "red":
                worst_tier = "yellow"
                risk_alerts.extend(s.age_alerts)
        if worst_tier in ("yellow", "red") and customer_age is not None:
            _, _, alt_paths = assess_age_suitability(
                customer_age,
                max(
                    (s.term_years or 0) for s in all_scenarios
                ),
            )
        # Dedupe while preserving order
        seen_msgs: set[str] = set()
        sales_data.financing_risk_alerts = [
            a for a in risk_alerts if not (a in seen_msgs or seen_msgs.add(a))
        ]
        sales_data.alternative_financing_paths = alt_paths
        sales_data.financing_suitability_tier = worst_tier

        # Pick the recommended scenario
        rec = _pick_recommended_scenario(
            all_scenarios,
            financial_profile=sales_data.financial_profile,
            age=customer_age,
        )
        if rec:
            sales_data.recommended_scenario_tier = rec.tier_name
            sales_data.recommended_scenario_name = rec.name

        # One Gemini call to produce the affordability narrative.
        try:
            context_json = json.dumps(
                {
                    "customer": {
                        "name": sales_data.customer_name,
                        "age": customer_age,
                        "financial_profile": sales_data.financial_profile,
                        "monthly_energy_bill_eur": sales_data.monthly_energy_bill_eur,
                    },
                    "recommended": {
                        "tier": sales_data.recommended_scenario_tier,
                        "name": sales_data.recommended_scenario_name,
                    },
                    "scenarios": [s.model_dump() for s in all_scenarios],
                    "risk_alerts": sales_data.financing_risk_alerts,
                    "alternative_paths": sales_data.alternative_financing_paths,
                    "suitability_tier": sales_data.financing_suitability_tier,
                },
                indent=2,
                default=str,
            )
            response = await chat_completion(
                model=self.model,
                max_tokens=512,
                system=NARRATIVE_SYSTEM + "\n\nData:\n" + context_json,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Write the affordability briefing with credit risk assessment now."
                        ),
                    }
                ],
                tools=[NARRATIVE_TOOL],
            )
            for tc in response.tool_calls:
                if tc.name == "store_affordability_narrative":
                    narrative = str(tc.input.get("narrative", "")).strip()
                    if narrative:
                        sales_data.affordability_narrative = narrative
                    # Store credit risk fields in strategy_notes via shared_state
                    credit_risk = tc.input.get("credit_risk", "MEDIUM")
                    co_applicant = tc.input.get("co_applicant_flag", False)
                    fin_rec = tc.input.get("financing_recommendation", "Review needed")
                    # Append to narrative for display
                    risk_section = (
                        f"\n\n**Credit Risk Assessment:** {credit_risk}"
                        f"\n**Co-applicant needed:** {'Yes' if co_applicant else 'No'}"
                        f"\n**Financing Recommendation for Cloover:** {fin_rec}"
                    )
                    sales_data.affordability_narrative = (
                        (sales_data.affordability_narrative or "") + risk_section
                    )
            if not sales_data.affordability_narrative and response.text.strip():
                sales_data.affordability_narrative = response.text.strip()
        except Exception as exc:  # pragma: no cover - demo resilience
            logger.warning(f"FinancialAgent narrative LLM call failed: {exc}")

        # Advance phase
        if sales_data.is_financial_complete():
            sales_data.phase = SalesPhase.STRATEGY

        _save_sales_data(context, sales_data)

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=_build_summary(sales_data),
            agent_name=self.name,
            metadata={
                "phase": sales_data.phase.value,
                "sales_data": sales_data.model_dump(),
            },
        )

    async def plan(self, context: AgentContext, task: str) -> list[str]:
        return [
            "Break each bundle tier into component costs",
            "Apply KfW 270 / BEG EM / KfW 458 subsidy rules",
            "Compute 3 financing scenarios per tier (cash / subsidy+cash / subsidy+financing)",
            "Run age-based suitability check on each loan scenario",
            "Pick recommended scenario and write affordability narrative",
        ]

    async def can_handle(self, message: AgentMessage) -> float:
        return 0.2
