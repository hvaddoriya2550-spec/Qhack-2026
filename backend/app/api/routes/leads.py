import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

LEADS_FILE = Path(__file__).resolve().parents[3] / "data" / "leads.json"


def _load_leads() -> list[dict]:
    if not LEADS_FILE.exists():
        return []
    with open(LEADS_FILE) as f:
        return json.load(f)


@router.get("/")
async def list_leads() -> list[dict]:
    """List all leads."""
    return _load_leads()


@router.get("/{lead_id}")
async def get_lead(lead_id: int) -> dict:
    """Get a single lead by ID."""
    for lead in _load_leads():
        if lead.get("id") == lead_id:
            return lead
    raise HTTPException(status_code=404, detail="Lead not found")
