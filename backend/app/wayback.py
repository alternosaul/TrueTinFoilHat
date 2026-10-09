"""Cliente mínimo de Wayback Machine: snapshot más cercano a una fecha + descarga del HTML original."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.config import get_settings

AVAILABILITY_URL = "https://archive.org/wayback/available"
CDX_URL = "https://web.archive.org/cdx/search/cdx"


@dataclass
class Snapshot:
    timestamp: str  # YYYYMMDDhhmmss
    url: str  # URL original archivada

    @property
    def raw_url(self) -> str:
        # `id_` devuelve el HTML original sin la barra/reescritura de Wayback
        return f"https://web.archive.org/web/{self.timestamp}id_/{self.url}"

    @property
    def view_url(self) -> str:
        return f"https://web.archive.org/web/{self.timestamp}/{self.url}"

    @property
    def date(self) -> datetime:
        return datetime.strptime(self.timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=60, follow_redirects=True, headers={"User-Agent": get_settings().user_agent}
    )


def target_timestamp(years_back: int, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(days=365 * years_back)).strftime("%Y%m%d")


async def closest_snapshot(url: str, timestamp: str) -> Snapshot | None:
    """Snapshot más cercano a `timestamp`. La availability API a veces no encuentra nada que sí está en CDX."""
    errors: list[Exception] = []
    for finder in (_closest_availability, _closest_cdx):
        try:
            if snap := await finder(url, timestamp):
                return snap
        except (httpx.HTTPError, ValueError) as e:
            errors.append(e)
    if len(errors) == 2:
        raise errors[-1]
    return None


async def _closest_availability(url: str, timestamp: str) -> Snapshot | None:
    async with _client() as client:
        r = await client.get(AVAILABILITY_URL, params={"url": url, "timestamp": timestamp})
        r.raise_for_status()
        closest = r.json().get("archived_snapshots", {}).get("closest")
    if not closest or not closest.get("available") or str(closest.get("status")) != "200":
        return None
    original = closest["url"].split(f"/web/{closest['timestamp']}/", 1)[-1]
    return Snapshot(timestamp=closest["timestamp"], url=original)


async def _closest_cdx(url: str, timestamp: str) -> Snapshot | None:
    async with _client() as client:
        r = await client.get(CDX_URL, params={
            "url": url, "closest": timestamp, "sort": "closest", "limit": 1,
            "filter": "statuscode:200", "fl": "timestamp,original", "output": "json",
        })
        r.raise_for_status()
        rows = r.json() if r.text.strip() else []  # ValueError si Wayback devuelve su página HTML de "offline"
    if len(rows) < 2:
        return None
    ts, original = rows[1]
    return Snapshot(timestamp=ts, url=original)


async def list_snapshots(url: str, limit: int = 50) -> list[Snapshot]:
    """Snapshots con contenido distinto (collapse por digest), del más reciente al más antiguo."""
    async with _client() as client:
        r = await client.get(CDX_URL, params={
            "url": url, "output": "json", "fl": "timestamp,original",
            "filter": "statuscode:200", "collapse": "digest", "limit": -limit,
        })
        r.raise_for_status()
        rows = r.json() if r.text.strip() else []
    return [Snapshot(timestamp=ts, url=orig) for ts, orig in rows[1:]][::-1]


async def fetch_snapshot_html(snap: Snapshot) -> str:
    async with _client() as client:
        r = await client.get(snap.raw_url)
        r.raise_for_status()
        return r.text
