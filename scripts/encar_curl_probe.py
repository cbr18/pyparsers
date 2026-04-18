#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LIST_URL = "http://api.encar.com/search/car/list/premium"
DETAIL_URL = "http://api.encar.com/v1/readside/vehicle/{car_id}"
DEFAULT_QUERY = "(And.Hidden.N._.CarType.Y.)"


def fetch_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.encar.com",
            "Referer": "https://www.encar.com/",
            "User-Agent": "Mozilla/5.0 EncarProbe/1.0",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Encar list/detail JSON endpoints.")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--car-id")
    args = parser.parse_args()

    offset = max(args.page - 1, 0) * args.limit
    list_url = f"{LIST_URL}?{urlencode({'count': 'true', 'q': DEFAULT_QUERY, 'sr': f'|ModifiedDate|{offset}|{args.limit}'})}"
    listing = fetch_json(list_url)
    results = listing.get("SearchResults") or []
    print(json.dumps({"list_url": list_url, "count": listing.get("Count"), "items": len(results)}, ensure_ascii=False, indent=2))

    car_id = args.car_id or (str(results[0]["Id"]) if results else None)
    if car_id:
        detail_url = DETAIL_URL.format(car_id=car_id)
        detail = fetch_json(detail_url)
        print(json.dumps({"detail_url": detail_url, "top_level_keys": sorted(detail.keys())}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
