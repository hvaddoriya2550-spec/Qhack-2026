"""PVGIS (EU Joint Research Centre) PV yield estimator.

Free, no API key. Given latitude/longitude and a system size in kWp,
returns annual production (kWh), monthly breakdown, and the optimal
tilt/azimuth that PVGIS computed.

API reference:
https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"

# Typical system losses (%) — cable/inverter/soiling etc. PVGIS default is 14.
DEFAULT_SYSTEM_LOSS = 14.0


@dataclass
class PVGISResult:
    annual_kwh: float  # E_y — yearly energy production
    specific_yield_kwh_per_kwp: float  # E_y / peakpower
    optimal_tilt_deg: float | None
    optimal_azimuth_deg: float | None
    monthly_kwh: list[float] = field(default_factory=list)  # Jan..Dec
    raw: dict | None = None  # full PVGIS payload for debugging


class PVGISError(RuntimeError):
    """Raised when the PVGIS call fails or the payload is unexpected."""


async def estimate_pv_yield(
    *,
    lat: float,
    lon: float,
    kwp: float,
    loss_pct: float = DEFAULT_SYSTEM_LOSS,
    optimal_angles: bool = True,
    client: httpx.AsyncClient | None = None,
    timeout: float = 30.0,
) -> PVGISResult:
    """Call PVGIS PVcalc and return a normalized yield estimate."""
    params: dict[str, str | float | int] = {
        "lat": lat,
        "lon": lon,
        "peakpower": kwp,
        "loss": loss_pct,
        "outputformat": "json",
    }
    if optimal_angles:
        params["optimalangles"] = 1

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout)
    try:
        resp = await http.get(PVGIS_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as exc:
        raise PVGISError(f"PVGIS request failed: {exc}") from exc
    finally:
        if owns_client:
            await http.aclose()

    try:
        outputs = payload["outputs"]
        totals = outputs["totals"]["fixed"]
        annual_kwh = float(totals["E_y"])

        # Monthly production — list of {"month": 1..12, "E_m": ...}
        monthly_raw = outputs.get("monthly", {}).get("fixed", [])
        monthly = [float(m["E_m"]) for m in sorted(monthly_raw, key=lambda x: x["month"])]

        # Optimal angles, if PVGIS computed them
        mounting = payload.get("inputs", {}).get("mounting_system", {}).get("fixed", {})
        tilt = mounting.get("slope", {}).get("value")
        azimuth = mounting.get("azimuth", {}).get("value")
    except (KeyError, TypeError, ValueError) as exc:
        raise PVGISError(f"Unexpected PVGIS response shape: {exc}") from exc

    return PVGISResult(
        annual_kwh=annual_kwh,
        specific_yield_kwh_per_kwp=annual_kwh / kwp if kwp else 0.0,
        optimal_tilt_deg=float(tilt) if tilt is not None else None,
        optimal_azimuth_deg=float(azimuth) if azimuth is not None else None,
        monthly_kwh=monthly,
        raw=payload,
    )
