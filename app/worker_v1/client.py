from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    json: dict[str, Any] | None
    text: str


def _extract_json(resp: httpx.Response) -> dict[str, Any] | None:
    try:
        return resp.json()
    except ValueError:
        return None


async def post_json(
    client: httpx.AsyncClient,
    url: str,
    token: str,
    payload: dict[str, Any],
) -> ApiResponse:
    resp = await client.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    return ApiResponse(status_code=resp.status_code, json=_extract_json(resp), text=resp.text)
