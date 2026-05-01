from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


def _age_from_dob(dob: str | None) -> int | None:
    """Compute age in whole years from an ISO 'YYYY-MM-DD' DOB string."""
    if not dob:
        return None
    try:
        d = datetime.strptime(dob.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    today = date.today()
    return today.year - d.year - ((today.month, today.day) < (d.month, d.day))


class SalesPhase(str, Enum):
    DATA_GATHERING = "data_gathering"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    FINANCIAL = "financial"
    STRATEGY = "strategy"
    DELIVERABLE = "deliverable"
    COMPLETE = "complete"


class ProductRecommendation(BaseModel):
    """A product the installer can offer this customer."""
    name: str  # e.g. "Solar PV 10 kWp", "Heat pump Vaillant aroTHERM"
    description: str = ""
    estimated_price_eur: str = ""
    key_benefits: list[str] = []


class CompetitorInfo(BaseModel):
    name: str
    description: str = ""
    strengths: list[str] = []
    weaknesses: list[str] = []
    market_share: str = ""


class ObjectionResponse(BaseModel):
    objection: str
    response: str


class BundleTier(BaseModel):
    """One of the 3 tiered offer packages (Pillar 1 of the challenge)."""

    name: str  # "Starter" | "Recommended" | "Full Independence"
    items: list[ProductRecommendation] = []
    upfront_cost_eur: int = 0
    annual_savings_eur: int = 0
    annual_co2_saved_kg: int = 0
    energy_independence_pct: int = 0  # 0..100
    payback_years: float = 0.0
    narrative: str = ""  # causal story: "HP → more electricity → solar covers it → ..."


class SubsidyLine(BaseModel):
    """One applied subsidy for one component in the bundle."""

    program: str  # "KfW 270", "BEG EM / BAFA", "KfW 458", ...
    component: str  # "Solar PV", "Battery", "Heat pump", "Wallbox"
    kind: str  # "grant" | "loan"
    amount_eur: int  # grant value OR eligible loan principal
    interest_rate_pct: float | None = None  # only for loans
    max_term_years: int | None = None  # only for loans
    eligibility_notes: str = ""


class FinancingScenario(BaseModel):
    """One payment path for one bundle tier.

    The sales rep sees these side-by-side so they can steer the
    conversation based on the customer's cash/risk profile.
    """

    tier_name: str  # which BundleTier this belongs to
    name: str  # "Cash", "Subsidy + Cash", "Subsidy + KfW 270 financing"
    upfront_eur: int  # what the customer pays on day 1
    financed_eur: int = 0  # principal financed (0 for pure cash)
    monthly_payment_eur: int = 0
    interest_rate_pct: float | None = None
    term_years: int | None = None
    total_cost_eur: int = 0  # upfront + all monthly payments
    total_savings_10y_eur: int = 0  # energy savings − payments (10y)
    total_savings_20y_eur: int = 0  # 20y
    age_suitability_tier: str = "green"  # "green" | "yellow" | "red"
    age_alerts: list[str] = []
    narrative: str = ""


class SalesData(BaseModel):
    """Structured data accumulated by agents throughout the sales pipeline.

    Context: An energy installer (solar, heat pumps, wallboxes, batteries)
    uses this to build a personalized pitch for a residential customer.
    """

    # Phase tracking
    phase: SalesPhase = SalesPhase.DATA_GATHERING

    # ── Customer & property info (data gathering) ───────────────
    customer_name: str | None = None
    date_of_birth: str | None = None  # ISO "YYYY-MM-DD"
    postal_code: str | None = None
    city: str | None = None
    product_interest: str | None = None  # "Solar", "Heat pump", "Wallbox", etc.
    household_size: int | None = None
    house_type: str | None = None  # "Detached", "Semi-detached", "Townhouse", etc.
    build_year: int | None = None
    roof_orientation: str | None = None
    electricity_kwh_year: int | None = None
    heating_type: str | None = None  # "Gas", "Oil", "Heat pump", "District heating"
    monthly_energy_bill_eur: int | None = None
    existing_assets: str | None = None  # "None", "Solar 5 kWp", etc.
    financial_profile: str | None = None
    notes: str | None = None

    @property
    def age(self) -> int | None:
        """Derived age in years from date_of_birth (never persisted)."""
        return _age_from_dob(self.date_of_birth)

    # ── Product recommendations ─────────────────────────────────
    recommendations: list[ProductRecommendation] = []

    # ── Research fields ─────────────────────────────────────────
    competitors: list[CompetitorInfo] = []
    market_trends: list[str] = []
    regional_incentives: list[str] = []  # subsidies, tax credits, local programs
    energy_price_outlook: str | None = None
    industry_insights: list[str] = []

    # ── Analysis fields (inferred from APIs + LLM reasoning) ────
    # Geocoding (Nominatim)
    latitude: float | None = None
    longitude: float | None = None
    location_display_name: str | None = None

    # House-type inference (LLM-based probability distribution)
    house_type_probability: dict[str, float] | None = None
    house_type_reasoning: str | None = None

    # Solar potential (PVGIS)
    assumed_system_kwp: float | None = None
    solar_potential_kwh_year: int | None = None
    solar_specific_yield_kwh_per_kwp: float | None = None
    solar_optimal_tilt_deg: float | None = None
    solar_optimal_azimuth_deg: float | None = None
    solar_monthly_kwh: list[float] = []
    solar_notes: str | None = None

    # Electricity prices (SMARD wholesale + retail estimate)
    wholesale_price_eur_mwh_avg: float | None = None
    wholesale_price_eur_mwh_latest: float | None = None
    local_electricity_price_eur_kwh: float | None = None  # retail estimate
    electricity_price_notes: str | None = None

    # Heating (LLM inference from house + heating type + build year)
    current_heating_cost_eur_year: int | None = None
    heating_cost_notes: str | None = None

    # Synthesized optimal bundle (LLM — solar + battery + HP + wallbox)
    optimal_bundle: list[ProductRecommendation] = []
    optimal_bundle_rationale: str | None = None
    optimal_bundle_total_cost_eur: int | None = None

    # ── Tiered bundles (Pillar 1 of challenge) ──────────────────
    # Starter / Recommended / Full Independence. AnalysisAgent
    # produces these; FinancialAgent consumes them to build scenarios.
    bundle_tiers: list[BundleTier] = []

    # ── Financial pipeline outputs (Pillar 2 of challenge) ──────
    subsidy_breakdown: list[SubsidyLine] = []
    financing_scenarios: list[FinancingScenario] = []
    affordability_narrative: str | None = None
    effective_out_of_pocket_eur: int | None = None
    recommended_scenario_tier: str | None = None  # "Starter" | "Recommended" | "Full Independence"
    recommended_scenario_name: str | None = None

    # ── Age-based financing suitability (consumed by FinancialAgent) ────
    # Tier: "green" (broadly normal), "yellow" (needs review),
    # "red" (strong mismatch). Never an automatic decline — this is a
    # sales-coach alert, not an underwriting decision.
    financing_suitability_tier: str | None = None
    financing_risk_alerts: list[str] = []
    alternative_financing_paths: list[str] = []

    # ── Strategy fields ─────────────────────────────────────────
    positioning: str | None = None
    value_proposition: str | None = None
    key_messages: list[str] = []
    objections: list[ObjectionResponse] = []
    savings_estimate: str | None = None  # e.g. "~€1,200/year"
    payback_period: str | None = None  # e.g. "~8 years"
    financing_options: list[str] = []

    def is_gathering_complete(self) -> bool:
        """Minimum data to proceed: we need the customer, property, and interest."""
        return bool(
            self.customer_name
            and self.product_interest
            and self.house_type
            and self.heating_type
        )

    def is_research_complete(self) -> bool:
        return bool(self.regional_incentives or self.market_trends)

    def is_analysis_complete(self) -> bool:
        """Analysis is complete once we have solar + price + bundle inferred."""
        return bool(
            self.solar_potential_kwh_year is not None
            and self.local_electricity_price_eur_kwh is not None
            and (self.bundle_tiers or self.optimal_bundle)
        )

    def is_financial_complete(self) -> bool:
        """Financial is complete once we have scenarios for each tier."""
        return bool(self.financing_scenarios)

    def is_strategy_complete(self) -> bool:
        return bool(self.value_proposition and self.key_messages)
