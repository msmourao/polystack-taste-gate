#!/usr/bin/env python3
"""PolyStack Taste Gate — Qloo-backed Locate → Diagnose → Apply|Refuse."""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT / ".env")

BASE = (os.getenv("QLOO_BASE_URL") or "https://hackathon.api.qloo.com").rstrip("/")
API_KEY = (os.getenv("QLOO_API_KEY") or "").strip()
PORT = int(os.getenv("PORT") or "8787")

app = FastAPI(title="PolyStack Taste Gate", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


class TasteRequest(BaseModel):
    seed: str = Field(..., min_length=1, description="Cultural seed: brand, artist, movie…")
    target_type: str = Field(
        default="urn:entity:brand",
        description="Insights filter.type",
    )


def _headers() -> dict[str, str]:
    if not API_KEY:
        return {}
    return {"X-Api-Key": API_KEY}


def _fixture_response(seed: str) -> dict:
    raw = json.loads((ROOT / "fixtures" / "seed_insights.json").read_text(encoding="utf-8"))
    raw["seed_query"] = seed
    return raw


async def qloo_search(client: httpx.AsyncClient, query: str) -> list[dict]:
    r = await client.get(
        f"{BASE}/search",
        params={"query": query, "types": "urn:entity:artist,urn:entity:brand,urn:entity:movie"},
        headers=_headers(),
        timeout=30.0,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or data.get("entities") or data.get("data") or []
    out: list[dict] = []
    for item in results[:5]:
        if not isinstance(item, dict):
            continue
        eid = item.get("entity_id") or item.get("id") or item.get("qloo_id")
        name = item.get("name") or item.get("title") or str(eid)
        typ = item.get("type") or item.get("entity_type") or ""
        if eid:
            out.append({"name": name, "entity_id": eid, "type": typ, "raw_keys": sorted(item.keys())[:12]})
    return out


async def qloo_insights(client: httpx.AsyncClient, entity_id: str, filter_type: str) -> list[dict]:
    r = await client.get(
        f"{BASE}/v2/insights",
        params={
            "filter.type": filter_type,
            "signal.interests.entities": entity_id,
        },
        headers=_headers(),
        timeout=45.0,
    )
    r.raise_for_status()
    data = r.json()
    entities = data.get("entities") or data.get("results") or []
    out: list[dict] = []
    for item in entities[:8]:
        if not isinstance(item, dict):
            continue
        eid = item.get("entity_id") or item.get("id")
        name = item.get("name") or item.get("title") or str(eid)
        if eid:
            out.append(
                {
                    "name": name,
                    "entity_id": eid,
                    "type": item.get("type") or filter_type,
                    "affinity_note": "Qloo insights entity",
                }
            )
    return out


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "live_qloo": bool(API_KEY),
        "base": BASE,
        "mode": "live" if API_KEY else "fixture",
    }


@app.post("/api/taste-gate")
async def taste_gate(body: TasteRequest) -> dict:
    seed = body.seed.strip()
    if not seed:
        raise HTTPException(400, "seed required")

    if not API_KEY:
        return _fixture_response(seed)

    async with httpx.AsyncClient() as client:
        try:
            located = await qloo_search(client, seed)
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Qloo search failed: {exc}") from exc

        if not located:
            return {
                "mode": "live",
                "seed_query": seed,
                "located": [],
                "entities": [],
                "decision": "refuse",
                "reason": "Locate found no Qloo entities for this seed — refusing to invent taste.",
            }

        primary = located[0]
        try:
            entities = await qloo_insights(client, str(primary["entity_id"]), body.target_type)
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Qloo insights failed: {exc}") from exc

        if not entities:
            return {
                "mode": "live",
                "seed_query": seed,
                "located": located,
                "insights_type": body.target_type,
                "entities": [],
                "decision": "refuse",
                "reason": "Diagnose returned empty insights — refusing hallucinated cultural affinity.",
            }

        return {
            "mode": "live",
            "seed_query": seed,
            "located": located,
            "insights_type": body.target_type,
            "entities": entities,
            "decision": "apply",
            "reason": "Cultural candidates grounded in Qloo entity receipts.",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
