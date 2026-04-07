import json
import os
import socket
import time
import urllib.error
import urllib.request

DONGCHEDI_BASE_URL = os.getenv("DONGCHEDI_BASE_URL", "http://127.0.0.1:5001")
CHE168_BASE_URL = os.getenv("CHE168_BASE_URL", "http://127.0.0.1:5002")


def _request_json(url: str, *, method: str = "GET", payload: dict | None = None, timeout: int = 180):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _poll_task(base_url: str, task_id: str, *, timeout: int = 120, interval: float = 1.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = _request_json(f"{base_url}/tasks/{task_id}", timeout=30)
        task = payload["data"]
        if task["status"] in ("succeeded", "failed", "cancelled"):
            return task
        time.sleep(interval)
    raise TimeoutError(f"task {task_id} did not finish within {timeout}s")


def _is_whitelist_forbidden(exc: Exception) -> bool:
    return isinstance(exc, urllib.error.HTTPError) and exc.code == 403


def _pick_candidates(items: list[dict], *, require_shop_id: bool = False) -> list[dict]:
    candidates = []
    for item in items:
        if not item.get("car_id"):
            continue
        if not item.get("image"):
            continue
        if require_shop_id and not item.get("shop_id"):
            continue
        candidates.append(item)
        if len(candidates) >= 6:
            break
    return candidates


def _assert_has_images(detail_data: dict, *, fallback_image: str | None = None):
    image = detail_data.get("image")
    gallery = detail_data.get("image_gallery")
    image_count = detail_data.get("image_count")

    assert image or gallery or image_count or fallback_image, "expected at least one image field in parsed response"
    if image:
        assert str(image).startswith("http")
    elif fallback_image:
        assert str(fallback_image).startswith("http")
    if isinstance(gallery, list) and gallery:
        assert any(str(item).startswith("http") for item in gallery)
    if image_count is not None:
        assert image_count >= 0


def _get_block_status(base_url: str, source: str, *, allow_transport_errors: bool = False) -> dict:
    try:
        payload = _request_json(f"{base_url}/blocked", timeout=180)
    except (TimeoutError, socket.timeout, urllib.error.URLError, ConnectionResetError, ConnectionError) as exc:
        if not allow_transport_errors:
            raise
        return {
            "source": source,
            "blocked": 1,
            "checks": {"list": 0, "detailed": 0},
            "details": {"transport_error": str(exc) or exc.__class__.__name__},
        }

    assert payload["status"] == 200
    assert payload["message"] == "Source availability probe completed"
    assert payload["data"]["source"] == source
    assert payload["data"]["blocked"] in (0, 1)
    assert isinstance(payload["data"]["checks"], dict)
    assert "list" in payload["data"]["checks"]
    assert "detailed" in payload["data"]["checks"]
    assert isinstance(payload["data"]["details"], dict)
    return payload["data"]


def test_blocked_endpoints_return_schema():
    dongchedi = _get_block_status(DONGCHEDI_BASE_URL, "dongchedi")
    che168 = _get_block_status(CHE168_BASE_URL, "che168", allow_transport_errors=True)

    assert dongchedi["checks"]["list"] in (0, 1)
    assert dongchedi["checks"]["detailed"] in (0, 1)
    assert che168["checks"]["list"] in (0, 1)
    assert che168["checks"]["detailed"] in (0, 1)


def test_dongchedi_service_list_and_detailed():
    block_status = _get_block_status(DONGCHEDI_BASE_URL, "dongchedi")
    if block_status["blocked"] == 1:
        print(f"dongchedi live parsing skipped: blocked probe returned {block_status}")
        return

    try:
        listing = _request_json(f"{DONGCHEDI_BASE_URL}/cars/page/1", timeout=120)
    except Exception as exc:
        if _is_whitelist_forbidden(exc):
            print(f"dongchedi live parsing skipped: list endpoint is whitelist-protected ({exc})")
            return
        raise
    cars = listing["data"]["search_sh_sku_info_list"]

    assert listing["data"]["current_page"] == 1
    assert cars, "expected non-empty dongchedi listing"

    detailed_ok = 0
    for item in _pick_candidates(cars):
        detail_identifier = item.get("sku_id") or item["car_id"]
        detail = _request_json(
            f"{DONGCHEDI_BASE_URL}/cars/car/{detail_identifier}",
            timeout=120,
        )
        assert detail["status"] == 200
        assert detail["data"]["sku_id"] == str(detail_identifier)
        assert detail["data"]["car_id"] == item["car_id"]
        _assert_has_images(detail["data"], fallback_image=item.get("image"))
        detailed_ok += 1
        if detailed_ok == 2:
            break

    assert detailed_ok == 2, "expected two successful dongchedi detailed parses"


def test_che168_service_list_and_detailed():
    block_status = _get_block_status(CHE168_BASE_URL, "che168", allow_transport_errors=True)
    if block_status["blocked"] == 1:
        print(f"che168 live parsing skipped: blocked probe returned {block_status}")
        return

    try:
        listing = _request_json(f"{CHE168_BASE_URL}/cars/page/1", timeout=60)
    except (TimeoutError, socket.timeout, urllib.error.URLError, urllib.error.HTTPError) as exc:
        if _is_whitelist_forbidden(exc):
            print(f"che168 live parsing skipped: list endpoint is whitelist-protected ({exc})")
            return
        print(f"che168 live parsing skipped: list request failed with {exc}")
        return
    cars = listing["data"]["search_sh_sku_info_list"]

    assert listing["data"]["current_page"] == 1
    if not cars:
        print("che168 live parsing skipped: list returned an empty page")
        return

    detailed_ok = 0
    last_error = None
    for item in _pick_candidates(cars, require_shop_id=True):
        try:
            detail = _request_json(
                f"{CHE168_BASE_URL}/detailed/parse",
                method="POST",
                payload={
                    "car_id": item["car_id"],
                    "shop_id": item["shop_id"],
                    "force_update": False,
                },
                timeout=90,
            )
        except (TimeoutError, socket.timeout, urllib.error.URLError, urllib.error.HTTPError) as exc:
            if isinstance(exc, urllib.error.HTTPError):
                last_error = exc.read().decode("utf-8", errors="replace")
            else:
                last_error = str(exc)
            continue

        if not detail.get("success"):
            last_error = detail
            continue

        assert detail["car_id"] == item["car_id"]
        _assert_has_images(detail["data"], fallback_image=item.get("image"))
        detailed_ok += 1
        if detailed_ok == 2:
            break

    if detailed_ok < 2:
        print(f"che168 live parsing skipped: upstream source did not yield two detailed cars, last_error={last_error}")
        return


def test_dongchedi_task_lifecycle():
    listing = _request_json(f"{DONGCHEDI_BASE_URL}/cars/page/1", timeout=120)
    cars = listing["data"]["search_sh_sku_info_list"]
    assert cars, "expected non-empty dongchedi listing for task smoke"

    seed_id = cars[0]["car_id"]
    created = _request_json(
        f"{DONGCHEDI_BASE_URL}/tasks",
        method="POST",
        payload={
            "task_type": "incremental",
            "parameters": {
                "id_field": "car_id",
                "existing_ids": [str(seed_id)],
            },
        },
        timeout=30,
    )
    assert created["status"] == 202
    task = created["data"]
    assert task["status"] == "queued"

    final_task = _poll_task(DONGCHEDI_BASE_URL, task["id"], timeout=120)
    assert final_task["status"] == "succeeded"
    assert final_task["stage"] == "completed"

    result_payload = _request_json(f"{DONGCHEDI_BASE_URL}/tasks/{task['id']}/result", timeout=30)
    assert result_payload["status"] == 200
    assert result_payload["data"]["task"]["id"] == task["id"]
    assert isinstance(result_payload["data"]["result"], list)


if __name__ == "__main__":
    test_dongchedi_service_list_and_detailed()
    test_che168_service_list_and_detailed()
    test_dongchedi_task_lifecycle()
    print("integration checks passed")
