from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from ..base_parser import BaseCarParser
from ..dongchedi.parser import parse_float_value, parse_int_value
from .models.car import EncarCar
from .models.response import EncarApiResponse, EncarData

logger = logging.getLogger(__name__)


def _get_positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _get_positive_float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class EncarParser(BaseCarParser):
    """Parser for Encar used car listings."""

    LIST_API_URL = "http://api.encar.com/search/car/list/premium"
    DETAIL_API_URL = "http://api.encar.com/v1/readside/vehicle/{car_id}"
    IMAGE_BASE_URL = "https://ci.encar.com"
    DEFAULT_QUERY = "(And.Hidden.N._.CarType.Y.)"

    def __init__(self, page_size: int = 50):
        self.page_size = page_size
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.encar.com",
            "Referer": "https://www.encar.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        }

    def _build_params(self, page: int) -> dict[str, str]:
        offset = max(page - 1, 0) * self.page_size
        return {
            "count": "true",
            "q": self.DEFAULT_QUERY,
            "sr": f"|ModifiedDate|{offset}|{self.page_size}",
        }

    def _build_image_url(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.IMAGE_BASE_URL}{path}"

    def _extract_photo_urls(self, raw: dict[str, Any]) -> list[str]:
        photos = raw.get("Photos") or raw.get("photos") or []
        urls = []
        if isinstance(photos, list):
            for photo in photos:
                if not isinstance(photo, dict):
                    continue
                path = photo.get("location") or photo.get("path")
                url = self._build_image_url(path)
                if url:
                    urls.append(url)

        if not urls:
            url = self._build_image_url(raw.get("Photo") or raw.get("photo"))
            if url:
                urls.append(url)

        return urls

    def _normalize_year_month(self, raw_value: Any) -> tuple[Optional[int], Optional[str]]:
        if raw_value is None:
            return None, None
        value = str(raw_value).strip()
        if not value:
            return None, None
        match = re.search(r"((?:19|20)\d{2})(\d{2})?", value)
        if not match:
            return None, None
        year = parse_int_value(match.group(1))
        month = parse_int_value(match.group(2)) or 1
        if not year:
            return None, None
        month = min(max(month, 1), 12)
        return year, f"{year:04d}-{month:02d}-01"

    def _join_text(self, values: Any) -> Optional[str]:
        if values is None:
            return None
        if isinstance(values, list):
            return ", ".join(str(item) for item in values if item not in (None, ""))
        if isinstance(values, dict):
            return json.dumps(values, ensure_ascii=False)
        text = str(values).strip()
        return text or None

    def _current_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _parse_listing_car(self, raw: dict[str, Any]) -> EncarCar:
        car_id = parse_int_value(raw.get("Id"))
        car_id_str = str(raw.get("Id")) if raw.get("Id") is not None else None
        year, first_registration_time = self._normalize_year_month(raw.get("Year") or raw.get("FormYear"))
        photos = self._extract_photo_urls(raw)
        price = parse_float_value(raw.get("Price"))
        mileage = parse_int_value(raw.get("Mileage"))
        title_parts = [
            raw.get("Manufacturer"),
            raw.get("Model"),
            raw.get("Badge"),
            raw.get("BadgeDetail"),
        ]
        title = " ".join(str(part).strip() for part in title_parts if part not in (None, ""))
        now = self._current_timestamp()

        return EncarCar(
            uuid=str(uuid.uuid4()),
            title=title or None,
            sh_price=str(raw.get("Price")) if raw.get("Price") is not None else None,
            price=price,
            image=photos[0] if photos else None,
            image_gallery=" ".join(photos) if photos else None,
            image_count=len(photos),
            link=f"https://fem.encar.com/cars/detail/{car_id_str}" if car_id_str else None,
            car_name=title or None,
            car_year=year,
            year=year,
            car_mileage=str(mileage) if mileage is not None else None,
            mileage=mileage,
            car_source_city_name=raw.get("OfficeCityState"),
            city=raw.get("OfficeCityState"),
            brand_name=raw.get("Manufacturer"),
            series_name=raw.get("Model"),
            transmission=raw.get("Transmission"),
            fuel_type=raw.get("FuelType"),
            car_id=car_id,
            sku_id=car_id_str,
            source="encar",
            is_available=True,
            tags=self._join_text(raw.get("Trust")),
            tags_v2=self._join_text(raw.get("ServiceMark")),
            condition=self._join_text(raw.get("Condition")),
            dealer_info=self._build_listing_dealer_info(raw),
            certification=self._join_text(raw.get("BuyType")),
            first_registration_time=first_registration_time,
            created_at=now,
            updated_at=now,
        )

    def _build_listing_dealer_info(self, raw: dict[str, Any]) -> Optional[str]:
        parts = []
        for label, key in (
            ("Office", "OfficeName"),
            ("Dealer", "DealerName"),
            ("City", "OfficeCityState"),
        ):
            if raw.get(key):
                parts.append(f"{label}: {raw[key]}")
        return "; ".join(parts) if parts else None

    def _parse_detail_car(self, raw: dict[str, Any], car_id: str) -> EncarCar:
        category = raw.get("category") or {}
        advertisement = raw.get("advertisement") or {}
        spec = raw.get("spec") or {}
        contact = raw.get("contact") or {}
        manage = raw.get("manage") or {}
        partnership = raw.get("partnership") or {}
        dealer = partnership.get("dealer") or {}
        firm = dealer.get("firm") or {}
        contents = raw.get("contents") or {}

        photos = self._extract_photo_urls(raw)
        year, first_registration_time = self._normalize_year_month(
            category.get("yearMonth") or category.get("formYear")
        )
        price = parse_float_value(advertisement.get("price"))
        mileage = parse_int_value(spec.get("mileage"))
        title_parts = [
            category.get("manufacturerName"),
            category.get("modelName"),
            category.get("gradeName"),
            category.get("gradeDetailName"),
        ]
        title = " ".join(str(part).strip() for part in title_parts if part not in (None, ""))
        now = self._current_timestamp()

        dealer_parts = []
        if dealer.get("name"):
            dealer_parts.append(f"Dealer: {dealer['name']}")
        if firm.get("name"):
            dealer_parts.append(f"Firm: {firm['name']}")
        if contact.get("address"):
            dealer_parts.append(f"Address: {contact['address']}")
        if contact.get("no"):
            dealer_parts.append(f"Phone: {contact['no']}")

        warranty = category.get("warranty") or {}
        warranty_info = json.dumps(warranty, ensure_ascii=False) if warranty else None
        tags = []
        for key in ("trust", "hotMark"):
            value = advertisement.get(key)
            if value:
                tags.append(f"{key}: {self._join_text(value)}")

        return EncarCar(
            uuid=str(uuid.uuid4()),
            title=title or None,
            sh_price=str(advertisement.get("price")) if advertisement.get("price") is not None else None,
            price=price,
            image=photos[0] if photos else None,
            image_gallery=" ".join(photos) if photos else None,
            image_count=len(photos),
            link=f"https://fem.encar.com/cars/detail/{car_id}",
            car_name=title or None,
            car_year=year,
            year=year,
            car_mileage=str(mileage) if mileage is not None else None,
            mileage=mileage,
            brand_name=category.get("manufacturerName"),
            series_name=category.get("modelName"),
            brand_id=parse_int_value(category.get("manufacturerCd")),
            series_id=parse_int_value(category.get("modelCd")),
            shop_id=parse_int_value(firm.get("code")),
            car_id=parse_int_value(car_id),
            sku_id=str(car_id),
            source="encar",
            city=contact.get("address"),
            car_source_city_name=contact.get("address"),
            is_available=advertisement.get("status") == "ADVERTISE",
            description=contents.get("text"),
            color=spec.get("colorName") or spec.get("customColor"),
            exterior_color=spec.get("colorName") or spec.get("customColor"),
            transmission=spec.get("transmissionName"),
            fuel_type=spec.get("fuelName"),
            engine_volume_ml=parse_int_value(spec.get("displacement")),
            body_type=spec.get("bodyName"),
            seat_count=str(spec.get("seatCount")) if spec.get("seatCount") is not None else None,
            first_registration_time=first_registration_time,
            view_count=parse_int_value(manage.get("viewCount")) or 0,
            favorite_count=parse_int_value(manage.get("subscribeCount")) or 0,
            contact_info=contact.get("no"),
            dealer_info="; ".join(dealer_parts) if dealer_parts else None,
            warranty_info=warranty_info,
            certification="; ".join(tags) if tags else None,
            has_details=True,
            last_detail_update=now,
            created_at=now,
            updated_at=now,
        )

    def fetch_cars(self, source: Optional[str] = None) -> EncarApiResponse:
        return self.fetch_cars_by_page(1)

    def fetch_cars_by_page(self, page: int) -> EncarApiResponse:
        max_retries = _get_positive_int_env("ENCAR_LIST_MAX_RETRIES", 3)
        retry_delay = _get_positive_float_env("ENCAR_LIST_RETRY_DELAY_SECONDS", 2.0)
        last_error: Optional[Exception] = None

        try:
            for attempt in range(1, max_retries + 1):
                try:
                    response = requests.get(
                        self.LIST_API_URL,
                        params=self._build_params(page),
                        headers=self.headers,
                        timeout=30,
                    )
                    break
                except (requests.ConnectionError, requests.Timeout) as exc:
                    last_error = exc
                    if attempt >= max_retries:
                        raise
                    delay = retry_delay * attempt
                    logger.warning(
                        "Encar list page %s attempt %s/%s failed: %s; retrying in %.1fs",
                        page,
                        attempt,
                        max_retries,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            else:
                raise RuntimeError(f"Encar list request failed: {last_error}")

            response.raise_for_status()
            payload = response.json()
            items = payload.get("SearchResults") or []
            cars = [self._parse_listing_car(item) for item in items if isinstance(item, dict)]
            total = parse_int_value(payload.get("Count")) or len(cars)
            offset = max(page - 1, 0) * self.page_size
            has_more = offset + len(cars) < total

            if not cars:
                return EncarApiResponse(
                    data=EncarData(has_more=False, search_sh_sku_info_list=[], total=total),
                    message=f"Страница {page} не содержит машин",
                    status=404,
                )

            return EncarApiResponse(
                data=EncarData(has_more=has_more, search_sh_sku_info_list=cars, total=total),
                message="Success",
                status=200,
            )
        except Exception as exc:
            logger.error("Error fetching Encar page %s: %s", page, exc, exc_info=True)
            return EncarApiResponse(
                data=EncarData(has_more=False, search_sh_sku_info_list=[], total=0),
                message=f"Ошибка при получении данных: {exc}",
                status=500,
            )

    def fetch_car_detail(self, car_id: str):
        try:
            response = requests.get(
                self.DETAIL_API_URL.format(car_id=car_id),
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            car = self._parse_detail_car(payload, str(car_id))
            return car, {"status": 200, "car_id": str(car_id)}
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 500
            logger.warning("Encar detail HTTP error for %s: %s", car_id, exc)
            return None, {"status": status, "car_id": str(car_id), "error": str(exc)}
        except Exception as exc:
            logger.error("Error fetching Encar detail %s: %s", car_id, exc, exc_info=True)
            return None, {"status": 500, "car_id": str(car_id), "error": str(exc)}
