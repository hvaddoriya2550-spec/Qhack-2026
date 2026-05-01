"""Nominatim (OpenStreetMap) postal code → lat/lon geocoder.

Free, no API key. Rate-limited to 1 req/sec — fine for interactive use.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim's usage policy requires a descriptive User-Agent.
USER_AGENT = "qhack2026-agent-chat/0.1 (energy-sales-assistant)"


@dataclass
class GeocodeResult:
    lat: float
    lon: float
    display_name: str


class GeocodeError(RuntimeError):
    """Raised when geocoding fails or returns no match."""


async def geocode_postal_code(
    postal_code: str,
    country: str = "DE",
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float = 15.0,
) -> GeocodeResult:
    """Resolve a postal code to latitude/longitude via Nominatim.

    Raises GeocodeError if no match is found or the API call fails.
    """
    params = {
        "postalcode": postal_code,
        "country": country,
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": USER_AGENT}

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout)
    try:
        resp = await http.get(NOMINATIM_URL, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise GeocodeError(f"Nominatim request failed: {exc}") from exc
    finally:
        if owns_client:
            await http.aclose()

    if not data:
        raise GeocodeError(
            f"No Nominatim match for postal_code={postal_code!r} country={country!r}"
        )

    entry = data[0]
    try:
        return GeocodeResult(
            lat=float(entry["lat"]),
            lon=float(entry["lon"]),
            display_name=str(entry.get("display_name", "")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodeError(f"Unexpected Nominatim response shape: {entry!r}") from exc
