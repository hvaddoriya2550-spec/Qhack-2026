from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    customer_name: str | None = None
    date_of_birth: str | None = None  # ISO YYYY-MM-DD
    postal_code: str | None = None
    city: str | None = None
    product_interest: str | None = None
    household_size: int | None = None
    house_type: str | None = None
    build_year: int | None = None
    roof_orientation: str | None = None
    electricity_kwh_year: int | None = None
    heating_type: str | None = None
    monthly_energy_bill_eur: int | None = None
    existing_assets: str | None = None
    financial_profile: str | None = None
    notes: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    customer_name: str | None = None
    date_of_birth: str | None = None  # ISO YYYY-MM-DD
    postal_code: str | None = None
    city: str | None = None
    product_interest: str | None = None
    household_size: int | None = None
    house_type: str | None = None
    build_year: int | None = None
    roof_orientation: str | None = None
    electricity_kwh_year: int | None = None
    heating_type: str | None = None
    monthly_energy_bill_eur: int | None = None
    existing_assets: str | None = None
    financial_profile: str | None = None
    notes: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    customer_name: str | None = None
    date_of_birth: str | None = None  # ISO YYYY-MM-DD
    postal_code: str | None = None
    city: str | None = None
    product_interest: str | None = None
    household_size: int | None = None
    house_type: str | None = None
    build_year: int | None = None
    roof_orientation: str | None = None
    electricity_kwh_year: int | None = None
    heating_type: str | None = None
    monthly_energy_bill_eur: int | None = None
    existing_assets: str | None = None
    financial_profile: str | None = None
    notes: str | None = None
    recommendations: list = []
    competitors: list = []
    research_data: dict = {}
    strategy_notes: dict = {}
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
