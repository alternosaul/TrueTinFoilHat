import httpx
import respx
from fastapi.testclient import TestClient

from app import pipeline, wayback
from app.jobs import create_job
from app.main import app
from tests.fakes import FakeProvider

URL = "https://www.example.com/legal/terms"


def page(*clauses: str) -> str:
    body = "".join(f"<h2>{i + 1}. Section {i + 1}</h2><p>{c}</p>" for i, c in enumerate(clauses))
    return f"<html><head><title>Example Terms</title></head><body><article><h1>Terms</h1>{body}</article></body></html>"


OLD_CLAUSES = (
    "We collect your email address so that you can log in and receive important account notifications.",
    "We never sell your personal data to anyone, and we only share it with service providers under contract.",
    "You may close your account at any time and we will delete your data within thirty days of the request.",
)
NEW_CLAUSES = (
    "We collect your email address so that you can log in and receive important account notifications.",
    "We may sell your personal data to advertising partners and data brokers to improve our offerings.",
    "Any dispute will be resolved by binding arbitration and you waive any right to a class action lawsuit.",
    "We use cookies and similar technologies to measure engagement with our marketing campaigns online.",
)
OLD, NEW = page(*OLD_CLAUSES), page(*NEW_CLAUSES)


@respx.mock
async def test_full_pipeline_with_wayback_and_cache():
    respx.get(URL).mock(return_value=httpx.Response(200, text=NEW))
    respx.get(wayback.AVAILABILITY_URL).mock(return_value=httpx.Response(200, json={
        "archived_snapshots": {"closest": {"available": True, "status": "200", "timestamp": "20251001000000",
                                           "url": f"http://web.archive.org/web/20251001000000/{URL}"}}}))
    respx.get(f"https://web.archive.org/web/20251001000000id_/{URL}").mock(return_value=httpx.Response(200, text=OLD))

    provider = FakeProvider()
    job = create_job()
    await pipeline.run_analysis(job, URL, provider, "es", compare=True)
    assert job.status == "done", job.error
    assert job.result["comparison_id"] is not None
    first_count = provider.classified
    # 4 cláusulas nuevas + solo las 2 viejas que difieren (la primera es idéntica y se reutiliza)
    assert first_count == len(NEW_CLAUSES) + 2

    with TestClient(app) as client:
        companies = client.get("/api/companies").json()
        assert companies[0]["domain"] == "example.com"
        assert companies[0]["documents"][0]["doc_type"] == "tos"

        analysis = client.get(f"/api/analyses/{job.result['analysis_id']}").json()
        colors = {c["color"] for c in analysis["clauses"]}
        assert {"red", "yellow"} <= colors
        assert analysis["counts"]["red"] >= 2

        cmp = client.get(f"/api/comparisons/{job.result['comparison_id']}").json()
        assert {c["type"] for c in cmp["changes"]} >= {"modified", "added"}
        assert all("impact" in c for c in cmp["changes"])

        # export → import en la misma DB: todo se deduplica
        exported = client.get("/api/export").json()
        res = client.post("/api/import", json=exported).json()
        assert res["analyses_added"] == 0 and res["analyses_skipped"] >= 2

        assert "text/csv" in client.get("/api/export?format=csv").headers["content-type"]

    # segunda ejecución: mismo texto → cache, sin reclasificar
    job2 = create_job()
    await pipeline.run_analysis(job2, URL, provider, "es", compare=True)
    assert job2.status == "done"
    assert job2.result["cached"] is True
    assert provider.classified == first_count
    assert job2.result["comparison_id"] == job.result["comparison_id"]


def test_hosted_mode_rejects_ollama(monkeypatch):
    from app.config import get_settings
    from app.llm.base import LLMError
    from app.llm.factory import make_provider

    monkeypatch.setattr(get_settings(), "mode", "hosted")
    try:
        make_provider("ollama", None, None)
        raise AssertionError("debería fallar")
    except LLMError:
        pass
    try:
        make_provider("anthropic", None, None)
        raise AssertionError("debería exigir key")
    except LLMError:
        pass


def test_helpers():
    assert pipeline.domain_of("https://www.spotify.com/us/legal/") == "spotify.com"
    assert pipeline.company_name_from_domain("spotify.com") == "Spotify"
    assert pipeline.guess_doc_type("https://x.com/privacy", None) == "privacy"
    assert pipeline.score_of(1, 0, 1) == 50
