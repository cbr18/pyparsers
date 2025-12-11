"""
Ad-hoc Playwright probe for che168 detail pages.

Goals:
- Try fetching detail pages for known car_ids (blocked cases) via desktop and mobile.
- Extract power, first_registration_time, mileage and head_images from __NEXT_DATA__ or HTML.
- Provide quick visibility whether Playwright can bypass current API blocks.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright


CAR_IDS = [57086324, 56854918]  # recent blocked examples

# Where to dump diagnostics (HTML + screenshots)
OUT_DIR = os.environ.get("CHE168_PROBE_OUT", "tmp/che168_probe")

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class ExtractResult:
    car_id: int
    source: str
    power: Optional[int]
    power_raw: Optional[str]
    first_registration_time: Optional[str]
    first_reg_raw: Optional[str]
    mileage: Optional[str]
    image_count: int
    has_gallery: bool
    gallery_sample: List[str]
    errors: List[str]


def _find_numbers(text: str) -> List[str]:
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def _pick_power(data: Any) -> Tuple[Optional[int], Optional[str]]:
    """
    Search recursively for horsepower or kW and normalize to hp.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            lower = str(k).lower()
            pwr, raw = _pick_power(v)
            if pwr:
                return pwr, raw
            if any(x in lower for x in ["power", "马力", "ps"]):
                if isinstance(v, (int, float)):
                    return int(v), str(v)
                if isinstance(v, str):
                    m = re.search(r"(\d+)", v)
                    if m:
                        return int(m.group(1)), v
    if isinstance(data, list):
        for item in data:
            pwr, raw = _pick_power(item)
            if pwr:
                return pwr, raw
    if isinstance(data, str):
        # kW pattern
        kw_match = re.search(r"(\d+)\s*k[wW]", data)
        if kw_match:
            try:
                kw = float(kw_match.group(1))
                return int(round(kw * 1.35962)), data
            except Exception:
                pass
        hp_match = re.search(r"(\d+)\s*马力", data)
        if hp_match:
            return int(hp_match.group(1)), data
    return None, None


def _pick_first_reg(data: Any) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(data, dict):
        for k, v in data.items():
            lower = str(k).lower()
            if any(x in lower for x in ["first_registration", "regdate", "register_date"]):
                if isinstance(v, str):
                    normalized = _normalize_date(v)
                    return normalized or None, v
            reg, raw = _pick_first_reg(v)
            if reg:
                return reg, raw
    if isinstance(data, list):
        for item in data:
            reg, raw = _pick_first_reg(item)
            if reg:
                return reg, raw
    if isinstance(data, str):
        norm = _normalize_date(data)
        if norm:
            return norm, data
    return None, None


def _normalize_date(text: str) -> Optional[str]:
    # Accept YYYY-MM, YYYY/MM, YYYY年MM, YYYY-MM-DD variants
    if not text:
        return None
    patterns = [
        r"(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?",
        r"(\d{4})年(\d{1,2})月?",
        r"(\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            year = int(m.group(1))
            if 1900 <= year <= 2100:
                month = m.group(2) if len(m.groups()) >= 2 else None
                day = m.group(3) if len(m.groups()) >= 3 else None
                month = int(month) if month else 1
                day = int(day) if day else 1
                try:
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except Exception:
                    return f"{year:04d}-01-01"
    return None


def _extract_gallery_from_payload(data: Any) -> List[str]:
    if isinstance(data, dict):
        for k in ["head_images", "images", "piclist"]:
            if k in data and isinstance(data[k], list):
                return [str(x) for x in data[k] if x]
        for v in data.values():
            res = _extract_gallery_from_payload(v)
            if res:
                return res
    if isinstance(data, list):
        for item in data:
            res = _extract_gallery_from_payload(item)
            if res:
                return res
    return []


def probe_once(car_id: int, url: str, user_agent: str, source: str) -> ExtractResult:
    errors: List[str] = []
    power = power_raw = None
    first_reg = first_reg_raw = None
    mileage = None
    gallery: List[str] = []

    os.makedirs(OUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=user_agent, viewport={"width": 1280, "height": 720})
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            # try to grab __NEXT_DATA__ if present
            next_data = page.query_selector("#__NEXT_DATA__")
            payload = None
            if next_data:
                try:
                    payload = json.loads(next_data.inner_text())
                except Exception as e:
                    errors.append(f"next_data_parse: {e}")
            else:
                # fallback: try window.__NEXT_DATA__
                try:
                    payload = page.evaluate("() => window.__NEXT_DATA__ || null")
                except Exception as e:
                    errors.append(f"window_next_data: {e}")

            if payload:
                power, power_raw = _pick_power(payload)
                first_reg, first_reg_raw = _pick_first_reg(payload)
                gallery = _extract_gallery_from_payload(payload)
                # mileage from payload
                if not mileage:
                    m = re.search(r'"mileage"\s*:\s*"?(.*?)["}]', json.dumps(payload))
                    if m:
                        mileage = m.group(1)

            # HTML-based fallbacks
            html = page.content()
            if not power:
                hp_match = re.search(r"(\d+)\s*马力", html)
                if hp_match:
                    power = int(hp_match.group(1))
                    power_raw = hp_match.group(0)
            if not first_reg:
                first_reg = _normalize_date(html)
                first_reg_raw = first_reg if first_reg else None
            if not gallery:
                imgs = page.query_selector_all("img")
                gallery = []
                for img in imgs:
                    try:
                        src = img.get_attribute("src") or ""
                        if src.startswith("//"):
                            src = "https:" + src
                        if src.startswith("http"):
                            gallery.append(src)
                    except Exception:
                        continue
            # Save diagnostics if gallery is empty or power/date missing
            needs_dump = not gallery or not power or not first_reg
            if needs_dump:
                safe_name = f"{car_id}_{source}"
                html_path = os.path.join(OUT_DIR, f"{safe_name}.html")
                png_path = os.path.join(OUT_DIR, f"{safe_name}.png")
                try:
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html)
                except Exception as e:
                    errors.append(f"html_dump: {e}")
                try:
                    page.screenshot(path=png_path, full_page=True)
                except Exception as e:
                    errors.append(f"png_dump: {e}")

            browser.close()
        except Exception as e:
            errors.append(str(e))
            try:
                browser.close()
            except Exception:
                pass

    gallery = list(dict.fromkeys([g for g in gallery if g]))  # dedupe
    return ExtractResult(
        car_id=car_id,
        source=source,
        power=power,
        power_raw=power_raw,
        first_registration_time=first_reg,
        first_reg_raw=first_reg_raw,
        mileage=mileage,
        image_count=len(gallery),
        has_gallery=len(gallery) > 0,
        gallery_sample=gallery[:5],
        errors=errors,
    )


def main():
    results: List[ExtractResult] = []
    for car_id in CAR_IDS:
        mobile_url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
        desktop_url = f"https://www.che168.com/cardetail/{car_id}.html"
        results.append(probe_once(car_id, mobile_url, MOBILE_UA, "mobile"))
        results.append(probe_once(car_id, desktop_url, DESKTOP_UA, "desktop"))

    for r in results:
        print("=" * 80)
        print(f"car_id={r.car_id} via {r.source}")
        for k, v in asdict(r).items():
            if k in ("gallery_sample", "errors"):
                print(f"{k}: {v}")
            else:
                print(f"{k}: {v}")


if __name__ == "__main__":
    sys.exit(main())

