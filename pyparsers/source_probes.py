import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence


def build_blocked_payload(source: str, blocked: int, checks: Dict[str, int], details: Dict[str, Any]) -> dict:
    return {
        "data": {
            "source": source,
            "blocked": blocked,
            "checks": checks,
            "details": details,
        },
        "message": "Source availability probe completed",
        "status": 200,
    }


def probe_error_message(exc: Exception) -> str:
    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"
    message = str(exc).strip()
    return message or exc.__class__.__name__


def probe_item_value(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def pick_probe_candidate(items: List[Any], required_fields: Sequence[str]) -> Optional[Any]:
    for item in items:
        if all(probe_item_value(item, field) for field in required_fields):
            return item
    return None


def extract_listing_cars(listing: Any) -> tuple[Optional[dict], List[Any]]:
    list_payload = listing.get("data") if isinstance(listing, dict) else None
    cars = list_payload.get("search_sh_sku_info_list", []) if isinstance(list_payload, dict) else []
    return list_payload, cars


@dataclass(frozen=True)
class SourceProbe:
    source: str
    candidate_fields: Sequence[str]
    list_fetch: Callable[[], Awaitable[Any]]
    detail_fetch: Callable[[Any], Awaitable[Any]]
    summarize_detail: Callable[[Any, Dict[str, Any]], bool]
    list_timeout: int = 60
    detail_timeout: int = 120


async def run_source_probe(probe: SourceProbe) -> dict:
    checks = {"list": 0, "detailed": 0}
    details: Dict[str, Any] = {}

    try:
        listing = await asyncio.wait_for(probe.list_fetch(), timeout=probe.list_timeout)
    except Exception as exc:
        details["list_error"] = probe_error_message(exc)
        return build_blocked_payload(probe.source, 1, checks, details)

    list_payload, cars = extract_listing_cars(listing)
    if cars:
        checks["list"] = 1
        details["list_count"] = len(cars)
    else:
        details["list_count"] = 0
        if isinstance(listing, dict):
            details["list_status"] = listing.get("status")
            details["list_message"] = listing.get("message")
        return build_blocked_payload(probe.source, 1, checks, details)

    candidate = pick_probe_candidate(cars, probe.candidate_fields)
    if candidate is None:
        details["detail_reason"] = "no_probe_candidate"
        return build_blocked_payload(probe.source, 1, checks, details)

    for field in probe.candidate_fields:
        details[f"probe_{field}"] = probe_item_value(candidate, field)

    try:
        detail_response = await asyncio.wait_for(probe.detail_fetch(candidate), timeout=probe.detail_timeout)
    except Exception as exc:
        details["detail_error"] = probe_error_message(exc)
        return build_blocked_payload(probe.source, 1, checks, details)

    if probe.summarize_detail(detail_response, details):
        checks["detailed"] = 1
        return build_blocked_payload(probe.source, 0, checks, details)

    return build_blocked_payload(probe.source, 1, checks, details)
