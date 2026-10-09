"""Analiza una lista de servicios populares contra un backend en marcha para poblar la galería.

Uso:
  python scripts/seed_gallery.py --provider ollama --model qwen2.5:14b
  ANTHROPIC_API_KEY=sk-ant-... python scripts/seed_gallery.py --provider anthropic
"""

import argparse
import json
import os
import sys
import urllib.request

SERVICES = [
    "https://policies.google.com/terms",
    "https://policies.google.com/privacy",
    "https://www.facebook.com/legal/terms",
    "https://www.facebook.com/privacy/policy/",
    "https://www.tiktok.com/legal/page/us/terms-of-service/en",
    "https://www.spotify.com/us/legal/end-user-agreement/",
    "https://www.spotify.com/us/legal/privacy-policy/",
    "https://help.netflix.com/legal/termsofuse",
    "https://x.com/en/tos",
    "https://www.amazon.com/gp/help/customer/display.html?nodeId=508088",
    "https://discord.com/terms",
    "https://www.reddit.com/policies/user-agreement",
    "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
    "https://signal.org/legal/",
    "https://duckduckgo.com/privacy",
]


def post(base: str, path: str, body: dict, key: str | None) -> dict:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-LLM-Key"] = key
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def follow(base: str, job_id: str) -> dict:
    with urllib.request.urlopen(f"{base}/api/jobs/{job_id}/events") as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:])
            print(f"   {ev['message']}", flush=True)
            if ev["stage"] in ("done", "error"):
                return ev
    return {"stage": "error", "message": "stream cerrado"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--provider", choices=["ollama", "anthropic"], default="ollama")
    ap.add_argument("--model")
    ap.add_argument("--lang", default="es")
    ap.add_argument("--no-compare", action="store_true")
    ap.add_argument("urls", nargs="*", help="URLs (por defecto, la lista SERVICES)")
    args = ap.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY") if args.provider == "anthropic" else None
    if args.provider == "anthropic" and not key:
        sys.exit("Define ANTHROPIC_API_KEY para usar --provider anthropic")

    failed = []
    for url in args.urls or SERVICES:
        print(f"→ {url}", flush=True)
        job = post(args.base, "/api/analyze", {
            "url": url, "provider": args.provider, "model": args.model, "lang": args.lang,
            "compare": not args.no_compare,
        }, key)
        if follow(args.base, job["job_id"])["stage"] != "done":
            failed.append(url)
    print(f"\nListo. Fallaron {len(failed)}: {failed}" if failed else "\nListo.")


if __name__ == "__main__":
    main()
