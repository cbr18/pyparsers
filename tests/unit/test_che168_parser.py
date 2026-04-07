import unittest
from unittest import mock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pyparsers"))

from api.che168.parser import Che168Parser


class _FakeProcess:
    def wait(self, timeout=None):
        return None


class _FakeService:
    process = _FakeProcess()


class _FakeDriver:
    service = _FakeService()

    def quit(self):
        return None


class Che168ParserTests(unittest.TestCase):
    def test_safe_quit_driver_tolerates_missing_temp_dir(self):
        parser = Che168Parser()
        parser.driver = _FakeDriver()
        parser._temp_dir = None

        parser._safe_quit_driver()

        self.assertIsNone(parser.driver)
        self.assertIsNone(parser._temp_dir)

    def test_build_search_api_sign_matches_bundle_logic(self):
        parser = Che168Parser()
        params = {
            "pageindex": "1",
            "pagesize": "10",
            "cid": "0",
            "pid": "0",
            "pageid": "1775544553426",
            "scene_no": "0",
            "ssnew": "1",
            "_appid": "2sc.m",
            "v": "11.41.5",
            "_subappid": "",
        }

        sign = parser._build_search_api_sign(params)

        self.assertEqual(sign, "bf6191a3cde1bdc127ea2bc1ec4a01ef")

    def test_parse_api_car_maps_search_payload(self):
        parser = Che168Parser()
        api_car = {
            "carname": "奔驰S级 2018款 S 450 L 4MATIC 卓越特别版",
            "price": "55.9",
            "imageurl": "https://2sc2.autoimg.cn/example.jpg.webp",
            "mileage": "3.4",
            "cname": "苏州",
            "dealerid": 335626,
            "infoid": 57999413,
            "firstregyear": "2018年",
            "seriesid": 59,
            "cartags": {
                "p2": [{"title": "旗舰店"}, {"title": "诚信车"}],
                "p4": [{"title": "已检测"}],
            },
        }

        car = parser._parse_api_car(api_car)

        self.assertEqual(car.car_id, 57999413)
        self.assertEqual(car.shop_id, 335626)
        self.assertEqual(car.sh_price, "55.9")
        self.assertEqual(car.car_mileage, "34000")
        self.assertEqual(car.first_registration_time, "2018-01-01")
        self.assertEqual(car.brand_name, "奔驰")
        self.assertEqual(car.series_name, "S级")
        self.assertEqual(
            car.link,
            "https://m.che168.com/cardetail/index?infoid=57999413",
        )
        self.assertEqual(car.tags_v2, "旗舰店, 诚信车, 已检测")
        self.assertTrue(car.image.startswith("https://"))

    def test_fetch_cars_via_api_returns_listing(self):
        parser = Che168Parser()
        payload = {
            "returncode": 0,
            "message": "成功",
            "result": {
                "pageindex": 1,
                "pagecount": 3,
                "carlist": [
                    {
                        "carname": "测试车",
                        "price": "12.3",
                        "imageurl": "https://example.com/car.jpg",
                        "mileage": "1.2",
                        "cname": "杭州",
                        "dealerid": 100,
                        "infoid": 200,
                        "firstregyear": "2020年",
                        "cartags": {},
                    }
                ],
            },
        }

        fake_response = mock.Mock()
        fake_response.json.return_value = payload
        fake_response.raise_for_status.return_value = None

        with mock.patch("api.che168.parser.requests.get", return_value=fake_response) as mocked_get:
            response = parser._fetch_cars_via_api(1)

        self.assertEqual(response.status, 200)
        self.assertEqual(response.message, "Success (signed API)")
        self.assertEqual(response.data.total, 1)
        self.assertTrue(response.data.has_more)
        self.assertEqual(response.data.search_sh_sku_info_list[0].car_id, 200)
        mocked_get.assert_called_once()

    def test_extract_title_parts_falls_back_to_series_when_brand_unknown(self):
        parser = Che168Parser()

        brand_name, series_name = parser._extract_title_parts("Cayenne 2024款 Cayenne 3.0T")

        self.assertIsNone(brand_name)
        self.assertEqual(series_name, "Cayenne")


if __name__ == "__main__":
    unittest.main()
