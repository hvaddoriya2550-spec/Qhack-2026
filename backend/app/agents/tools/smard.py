"""SMARD (Bundesnetzagentur) German wholesale electricity price feed.

Free, no API key. Returns day-ahead price in €/MWh at various resolutions.
Note: wholesale day-ahead is NOT retail — German residential retail is
typically 30-40 ct/kWh while wholesale hovers around 5-15 ct/kWh.

Filters of interest:
    4169 — Day-ahead price (€/MWh)
    4068 — Solar generation (MW) — useful for the "why now" narrative
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import httpx

SMARD_INDEX_URL = "https://www.smard.de/app/chart_data/{filter_id}/{region}/index_{resolution}.json"
SMARD_SERIES_URL = (
    "https://www.smard.de/app/chart_data/{filter_id}/{region}/{filter_id}_{region}_{resolution}_{timestamp}.json"
)

Resolution = Literal["hour", "quarterhour", "day", "week", "month", "year"]

FILTER_DAY_AHEAD_PRICE = 4169
FILTER_SOLAR_GENERATION = 4068


@dataclass
class SmardSeries:
    filter_id: int
    region: str
    resolution: str
    points: list[tuple[int, float]] = field(default_factory=list)  # (epoch_ms, value)

    @property
    def values(self) -> list[float]:
        return [v for _, v in self.points if v is not None]

    @property
    def average(self) -> float | None:
        vals = self.values
        return sum(vals) / len(vals) if vals else None

    @property
    def latest(self) -> float | None:
        for _, v in reversed(self.points):
            if v is not None:
                return float(v)
        return None


class SmardError(RuntimeError):
    """Raised when the SMARD call fails or returns nothing usable."""


async def _fetch_index(
    filter_id: int,
    region: str,
    resolution: Resolution,
    *,
    http: httpx.AsyncClient,
    timeout: float,
) -> list[int]:
    url = SMARD_INDEX_URL.format(filter_id=filter_id, region=region, resolution=resolution)
    resp = await http.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    timestamps = data.get("timestamps") or []
    if not timestamps:
        raise SmardError(f"SMARD index returned no timestamps for filter={filter_id}")
    return [int(t) for t in timestamps]


async def _fetch_series_at(
    filter_id: int,
    region: str,
    resolution: Resolution,
    timestamp: int,
    *,
    http: httpx.AsyncClient,
    timeout: float,
) -> list[tuple[int, float]]:
    url = SMARD_SERIES_URL.format(
        filter_id=filter_id,
        region=region,
        resolution=resolution,
        timestamp=timestamp,
    )
    resp = await http.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    raw_series = data.get("series") or []
    points: list[tuple[int, float]] = []
    for entry in raw_series:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        ts, val = entry[0], entry[1]
        if val is None:
            continue
        try:
            points.append((int(ts), float(val)))
        except (TypeError, ValueError):
            continue
    return points


async def fetch_smard_series(
    *,
    filter_id: int = FILTER_DAY_AHEAD_PRICE,
    region: str = "DE",
    resolution: Resolution = "hour",
    window: int = 1,
    client: httpx.AsyncClient | None = None,
    timeout: float = 30.0,
) -> SmardSeries:
    """Fetch the latest `window` SMARD slices and return a merged series.

    `window=1` fetches only the most recent slice; higher values grab more
    history (useful for computing a multi-day average).
    """
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout)
    try:
        timestamps = await _fetch_index(filter_id, region, resolution, http=http, timeout=timeout)
        picked = timestamps[-max(1, window):]

        merged: list[tuple[int, float]] = []
        for ts in picked:
            try:
                merged.extend(
                    await _fetch_series_at(
                        filter_id, region, resolution, ts, http=http, timeout=timeout
                    )
                )
            except httpx.HTTPError:
                # One slice failing shouldn't kill the whole call.
                continue
    except httpx.HTTPError as exc:
        raise SmardError(f"SMARD request failed: {exc}") from exc
    finally:
        if owns_client:
            await http.aclose()

    if not merged:
        raise SmardError(
            f"SMARD returned no usable points (filter={filter_id}, res={resolution})"
        )

    merged.sort(key=lambda p: p[0])
    return SmardSeries(
        filter_id=filter_id,
        region=region,
        resolution=resolution,
        points=merged,
    )