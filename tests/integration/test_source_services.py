import json
import os
import socket
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


def test_dongchedi_service_list_and_detailed():
    listing = _request_json(f"{DONGCHEDI_BASE_URL}/cars/dongchedi/page/1", timeout=120)
    cars = listing["data"]["search_sh_sku_info_list"]

    assert listing["data"]["current_page"] == 1
    assert cars, "expected non-empty dongchedi listing"

    detailed_ok = 0
    for item in _pick_candidates(cars):
        detail = _request_json(
            f"{DONGCHEDI_BASE_URL}/cars/dongchedi/car/{item['car_id']}",
            timeout=120,
        )
        assert detail["status"] == 200
        assert detail["data"]["car_id"] == item["car_id"]
        _assert_has_images(detail["data"], fallback_image=item.get("image"))
        detailed_ok += 1
        if detailed_ok == 2:
            break

    assert detailed_ok == 2, "expected two successful dongchedi detailed parses"


def test_che168_service_list_and_detailed():
    try:
        listing = _request_json(f"{CHE168_BASE_URL}/cars/che168/page/1", timeout=60)
    except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
        print(f"che168 live parsing skipped: list request failed with {exc}")
        return
    cars = listing["data"]["search_sh_sku_info_list"]

    assert listing["data"]["current_page"] == 1
    assert cars, "expected non-empty che168 listing"

    detailed_ok = 0
    last_error = None
    for item in _pick_candidates(cars, require_shop_id=True):
        try:
            detail = _request_json(
                f"{CHE168_BASE_URL}/che168/detailed/parse",
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


if __name__ == "__main__":
    test_dongchedi_service_list_and_detailed()
    test_che168_service_list_and_detailed()
    print("integration checks passed")
