"""Discover Newtron models available to the configured API key."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

from app.core.config import settings


async def list_models() -> list[str]:
    api_key = settings.newtron_api_key.strip() or os.environ.get("NEWTRON_API_KEY", "").strip()
    if not api_key:
        print("NO_API_KEY")
        return []

    base = settings.newtron_base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base}/models", headers=headers)
        if response.status_code != 200:
            print(f"LIST_FAILED status={response.status_code}")
            return []
        body = response.json()
        data = body.get("data", [])
        return [item["id"] for item in data if isinstance(item, dict) and item.get("id")]


async def probe_model(model_id: str, api_key: str, base: str) -> tuple[int, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
        "max_tokens": 8,
        "temperature": 0,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{base}/chat/completions",
                headers=headers,
                json=payload,
            )
            detail = ""
            if response.status_code >= 400:
                try:
                    detail = str(response.json().get("detail", ""))[:80]
                except ValueError:
                    detail = response.text[:80]
            return response.status_code, detail
        except httpx.TimeoutException:
            return 408, "timeout"
        except httpx.HTTPError as exc:
            return 0, str(type(exc).__name__)


async def main() -> None:
    api_key = settings.newtron_api_key.strip() or os.environ.get("NEWTRON_API_KEY", "").strip()
    if not api_key:
        print("NEWTRON_API_KEY not configured")
        sys.exit(1)

    base = settings.newtron_base_url.rstrip("/")
    models = await list_models()
    print(f"models_listed={len(models)}")

    # Probe candidates: current default + known Nemotron family + instruct models
    priority_prefixes = (
        "nvidia/nemotron",
        "nvidia/llama",
        "meta/llama",
        "mistralai/",
    )
    candidates = [settings.llm_model]
    for model_id in models:
        if any(model_id.startswith(p) or model_id.startswith(p.replace("nvidia/", "")) for p in priority_prefixes):
            if model_id not in candidates:
                candidates.append(model_id)

    # Cap probe count
    candidates = candidates[:25]
    print("\n=== Probe results (status code) ===")
    working: list[str] = []
    for model_id in candidates:
        status, detail = await probe_model(model_id, api_key, base)
        mark = "OK" if status == 200 else "FAIL"
        print(f"{mark} {status} {model_id} {detail}")
        if status == 200:
            working.append(model_id)

    print(f"\nworking_count={len(working)}")
    for model_id in working:
        print(f"  {model_id}")


if __name__ == "__main__":
    asyncio.run(main())
