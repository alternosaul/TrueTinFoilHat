import httpx
import respx

from app import wayback


@respx.mock
async def test_closest_snapshot_parses_availability():
    respx.get(wayback.AVAILABILITY_URL).mock(return_value=httpx.Response(200, json={
        "archived_snapshots": {"closest": {
            "available": True, "status": "200", "timestamp": "20251001120000",
            "url": "http://web.archive.org/web/20251001120000/https://example.com/terms",
        }}
    }))
    snap = await wayback.closest_snapshot("https://example.com/terms", "20251008")
    assert snap is not None
    assert snap.url == "https://example.com/terms"
    assert snap.raw_url == "https://web.archive.org/web/20251001120000id_/https://example.com/terms"
    assert snap.date.year == 2025


@respx.mock
async def test_closest_snapshot_none():
    respx.get(wayback.AVAILABILITY_URL).mock(return_value=httpx.Response(200, json={"archived_snapshots": {}}))
    respx.get(wayback.CDX_URL).mock(return_value=httpx.Response(200, json=[]))
    assert await wayback.closest_snapshot("https://example.com/x", "20251008") is None


@respx.mock
async def test_closest_snapshot_falls_back_to_cdx():
    respx.get(wayback.AVAILABILITY_URL).mock(return_value=httpx.Response(200, json={"archived_snapshots": {}}))
    respx.get(wayback.CDX_URL).mock(return_value=httpx.Response(200, json=[
        ["timestamp", "original"], ["20251005161849", "https://signal.org/legal/"]]))
    snap = await wayback.closest_snapshot("https://signal.org/legal/", "20251008")
    assert snap and snap.timestamp == "20251005161849"


@respx.mock
async def test_closest_snapshot_offline_html_raises():
    respx.get(wayback.AVAILABILITY_URL).mock(return_value=httpx.Response(503))
    respx.get(wayback.CDX_URL).mock(return_value=httpx.Response(200, text="<html>Temporarily Offline</html>"))
    import pytest
    with pytest.raises(ValueError):
        await wayback.closest_snapshot("https://e.com/t", "20251008")


@respx.mock
async def test_list_snapshots_newest_first():
    respx.get(wayback.CDX_URL).mock(return_value=httpx.Response(200, json=[
        ["timestamp", "original"], ["20240101000000", "https://e.com/t"], ["20250101000000", "https://e.com/t"],
    ]))
    snaps = await wayback.list_snapshots("https://e.com/t")
    assert [s.timestamp for s in snaps] == ["20250101000000", "20240101000000"]


def test_target_timestamp():
    from datetime import datetime, timezone
    assert wayback.target_timestamp(1, datetime(2026, 10, 8, tzinfo=timezone.utc)) == "20251008"
