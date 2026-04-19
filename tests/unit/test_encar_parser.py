import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pyparsers"))

from api.encar.parser import EncarParser


class EncarParserTests(unittest.TestCase):
    def test_parse_listing_car_maps_search_payload(self):
        parser = EncarParser()
        raw = {
            "Id": "41728573",
            "Photos": [{"location": "/carpicture02/pic4172/41728116_001.jpg"}],
            "Manufacturer": "기아",
            "Model": "K5 3세대",
            "Badge": "2.0 LPI",
            "BadgeDetail": "트렌디",
            "Transmission": "오토",
            "FuelType": "LPG",
            "Year": 202202.0,
            "FormYear": "2022",
            "Mileage": 96917.0,
            "Price": 1700.0,
            "Trust": ["HomeService"],
            "ServiceMark": ["EncarDiagnosisP1"],
            "Condition": ["Inspection"],
            "OfficeCityState": "경기",
            "OfficeName": "오토플래닛",
            "DealerName": "부천지점",
        }

        car = parser._parse_listing_car(raw)

        self.assertEqual(car.car_id, 41728573)
        self.assertEqual(car.sku_id, "41728573")
        self.assertEqual(car.source, "encar")
        self.assertEqual(car.brand_name, "기아")
        self.assertEqual(car.series_name, "K5 3세대")
        self.assertEqual(car.year, 2022)
        self.assertEqual(car.first_registration_time, "2022-02-01")
        self.assertEqual(car.mileage, 96917)
        self.assertEqual(car.price, 1700.0)
        self.assertTrue(car.image.startswith("https://ci.encar.com/"))
        self.assertIn("HomeService", car.tags)
        self.assertIn("오토플래닛", car.dealer_info)

    def test_fetch_cars_by_page_uses_offset_and_has_more(self):
        parser = EncarParser(page_size=20)
        payload = {
            "Count": 21,
            "SearchResults": [
                {
                    "Id": "1",
                    "Manufacturer": "현대",
                    "Model": "그랜저",
                    "Year": 202401.0,
                    "Mileage": 10,
                    "Price": 3000,
                }
            ],
        }
        fake_response = mock.Mock()
        fake_response.json.return_value = payload
        fake_response.raise_for_status.return_value = None

        with mock.patch("api.encar.parser.requests.get", return_value=fake_response) as mocked_get:
            response = parser.fetch_cars_by_page(2)

        self.assertEqual(response.status, 200)
        self.assertEqual(response.data.total, 21)
        self.assertFalse(response.data.has_more)
        params = mocked_get.call_args.kwargs["params"]
        self.assertEqual(params["sr"], "|ModifiedDate|20|20")

    def test_parse_detail_car_maps_readside_payload(self):
        parser = EncarParser()
        raw = {
            "manage": {"viewCount": 10, "subscribeCount": 2},
            "category": {
                "manufacturerCd": "002",
                "manufacturerName": "기아",
                "modelCd": "149",
                "modelName": "K5",
                "gradeName": "2.0 LPI",
                "gradeDetailName": "트렌디",
                "yearMonth": "202202",
            },
            "advertisement": {"price": 1700, "status": "ADVERTISE", "trust": ["Warranty"]},
            "contact": {"no": "0506", "address": "경기 부천시"},
            "spec": {
                "mileage": 96917,
                "displacement": 1999,
                "transmissionName": "오토",
                "fuelName": "LPG",
                "colorName": "검정색",
                "seatCount": 5,
                "bodyName": "중형차",
            },
            "photos": [{"path": "/carpicture02/pic4172/41728116_001.jpg"}],
            "partnership": {"dealer": {"name": "부천지점", "firm": {"code": "7240", "name": "오토플래닛"}}},
            "contents": {"text": "판매자 설명"},
        }

        car = parser._parse_detail_car(raw, "41728573")

        self.assertEqual(car.car_id, 41728573)
        self.assertEqual(car.shop_id, 7240)
        self.assertEqual(car.engine_volume_ml, 1999)
        self.assertEqual(car.exterior_color, "검정색")
        self.assertEqual(car.view_count, 10)
        self.assertEqual(car.favorite_count, 2)
        self.assertTrue(car.is_available)
        self.assertIn("판매자 설명", car.description)


if __name__ == "__main__":
    unittest.main()
