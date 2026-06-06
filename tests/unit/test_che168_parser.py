import unittest
from unittest import mock
import asyncio
import threading
import time
import types

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pyparsers"))

if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")

    class _FakeAPIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            return lambda func: func

        def get(self, *args, **kwargs):
            return lambda func: func

    class _FakeHTTPException(Exception):
        def __init__(self, status_code=None, detail=None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    fastapi_stub.APIRouter = _FakeAPIRouter
    fastapi_stub.HTTPException = _FakeHTTPException
    sys.modules["fastapi"] = fastapi_stub

from api.che168.parser import Che168Parser
from api.che168 import detailed_api
from api.che168 import detailed_parser_api
from api.che168.detailed_parser_api import (
    Che168DetailedParserAPI,
    _desktop_urls_to_try,
    _filter_car_images,
    _prefer_high_res_che168_images,
    _upgrade_che168_image_url,
)


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

    def test_parse_api_car_uses_series_brand_aliases(self):
        parser = Che168Parser()

        car = parser._parse_api_car(
            {
                "carname": "Cayenne 2024款 Cayenne 3.0T",
                "price": "78.8",
                "imageurl": "https://example.com/cayenne.jpg",
                "mileage": "1.3",
                "cname": "苏州",
                "dealerid": 1,
                "infoid": 2,
                "firstregyear": "2025年",
                "seriesid": 172,
                "cartags": {},
            }
        )

        self.assertEqual(car.brand_name, "保时捷")
        self.assertEqual(car.series_name, "Cayenne")

    def test_upgrade_che168_image_url_promotes_smaller_variants(self):
        self.assertEqual(
            _upgrade_che168_image_url(
                "https://2sc2.autoimg.cn/escimg/auto/g33/M03/E7/4A/640x480_c42_autohomecar__abc.jpg.webp"
            ),
            "https://2sc2.autoimg.cn/escimg/auto/g33/M03/E7/4A/1024x768_c42_autohomecar__abc.jpg.webp",
        )
        self.assertEqual(
            _upgrade_che168_image_url(
                "https://2sc2.autoimg.cn/escimg/g26/M04/EA/6C/f_s_autohomecar__abc.jpg"
            ),
            "https://2sc2.autoimg.cn/escimg/g26/M04/EA/6C/f_s_autohomecar__abc.jpg",
        )

    def test_prefer_high_res_che168_images_upgrades_gallery(self):
        upgraded = _prefer_high_res_che168_images(
            [
                "https://2sc2.autoimg.cn/escimg/auto/g33/M03/E7/4A/640x480_c42_autohomecar__abc.jpg.webp",
                "https://2sc2.autoimg.cn/escimg/auto/g33/M03/E7/4A/1024x768_c42_autohomecar__def.jpg.webp",
            ]
        )

        self.assertEqual(
            upgraded,
            [
                "https://2sc2.autoimg.cn/escimg/auto/g33/M03/E7/4A/1024x768_c42_autohomecar__abc.jpg.webp",
                "https://2sc2.autoimg.cn/escimg/auto/g33/M03/E7/4A/1024x768_c42_autohomecar__def.jpg.webp",
            ],
        )

    def test_filter_car_images_rejects_che168_service_images(self):
        filtered = _filter_car_images(
            [
                "https://dx.autoimg.cn/2sc/2022/2022-12/cardetail_load_error.png?format=webp",
                "https://dx.autoimg.cn/2sc/2025rnw_sdcard_images/details_nvbar_return_black.png?format=webp",
            ]
        )

        self.assertEqual(filtered, [])

    def test_detail_api_uses_session_device_id(self):
        parser = Che168DetailedParserAPI()

        params = parser._api_params(57021858)

        self.assertEqual(params["infoid"], 57021858)
        self.assertEqual(params["_appid"], "2sc.m")
        self.assertNotEqual(params["deviceid"], "api_parser_57021858")
        self.assertRegex(params["deviceid"], r"^[0-9a-f]{32}$")
        self.assertEqual(params["deviceid"], parser._api_params(1)["deviceid"])

    def test_fallback_desktop_uses_concurrency_limit(self):
        parser = Che168DetailedParserAPI()
        original_semaphore = detailed_parser_api._fallback_semaphore
        detailed_parser_api._fallback_semaphore = threading.BoundedSemaphore(1)
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_unlocked(car_id, shop_id=None, return_html=False, allow_generic=True):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with lock:
                active -= 1
            return {"car_id": car_id}

        try:
            with mock.patch.object(parser, "_fetch_images_desktop_unlocked", side_effect=fake_unlocked):
                threads = [
                    threading.Thread(target=parser._fetch_images_desktop, args=(57021858,)),
                    threading.Thread(target=parser._fetch_images_desktop, args=(57021859,)),
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
        finally:
            detailed_parser_api._fallback_semaphore = original_semaphore

        self.assertEqual(max_active, 1)

    def test_detail_parse_passes_shop_id_to_carinfo_api(self):
        parser = Che168DetailedParserAPI()

        with (
            mock.patch.object(parser, "_fetch_params_api", return_value={}),
            mock.patch.object(
                parser,
                "_fetch_carinfo_api",
                return_value={
                    "power": 104,
                    "image": "https://example.test/a.jpg",
                    "image_gallery": "https://example.test/a.jpg",
                    "image_count": 1,
                    "first_registration_time": "2020-01-01",
                },
            ) as mocked_carinfo,
        ):
            parser.parse_car_details(57021858, shop_id=344884)

        mocked_carinfo.assert_called_once_with(57021858, has_gallery=False, shop_id=344884)

    def test_desktop_fallback_skips_generic_url_when_disabled(self):
        urls = _desktop_urls_to_try(57021858, shop_id=344884, allow_generic=False)

        self.assertEqual(urls, ["https://www.che168.com/dealer/344884/57021858.html"])

    def test_desktop_fallback_keeps_generic_url_without_shop_id(self):
        urls = _desktop_urls_to_try(57021858, shop_id=None, allow_generic=False)

        self.assertEqual(urls, ["https://www.che168.com/cardetail/57021858.html"])

    def test_mobile_fallback_gallery_skips_second_desktop_enrich(self):
        parser = Che168DetailedParserAPI()

        with (
            mock.patch.object(parser, "_fetch_params_api", return_value={"is_banned": True}),
            mock.patch.object(
                parser,
                "_fetch_carinfo_api",
                return_value={
                    "is_banned": True,
                    "image": "https://example.test/a.jpg",
                    "image_gallery": "https://example.test/a.jpg",
                    "image_count": 1,
                },
            ),
            mock.patch.object(parser, "_fetch_images_desktop", return_value={}) as mocked_desktop,
        ):
            car_data, is_banned = parser.parse_car_details(57021858, shop_id=344884)

        self.assertIsNotNone(car_data)
        self.assertFalse(is_banned)
        self.assertEqual(car_data.image_gallery, "https://example.test/a.jpg")
        mocked_desktop.assert_not_called()

    def test_failed_carinfo_fallback_is_not_repeated_by_parse(self):
        parser = Che168DetailedParserAPI()

        with (
            mock.patch.object(parser, "_fetch_params_api", return_value={"is_banned": True}),
            mock.patch.object(parser, "_fetch_carinfo_api", return_value={"is_banned": True}),
            mock.patch.object(parser, "_fetch_images_desktop", return_value={}) as mocked_desktop,
            mock.patch.object(parser, "_fetch_images_fallback", return_value={}) as mocked_mobile,
        ):
            car_data, is_banned = parser.parse_car_details(57021858, shop_id=344884)

        self.assertIsNone(car_data)
        self.assertTrue(is_banned)
        mocked_desktop.assert_not_called()
        mocked_mobile.assert_not_called()


class Che168DetailApiAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        detailed_api._inflight_detail_tasks.clear()
        detailed_api._detail_failure_cache.clear()

    async def asyncTearDown(self):
        detailed_api._inflight_detail_tasks.clear()
        detailed_api._detail_failure_cache.clear()

    async def test_parse_car_details_coalesces_same_car_id(self):
        calls = 0

        async def fake_run_detail_parse(car_id, shop_id=None):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.05)
            return None, False

        with mock.patch.object(detailed_api, "_run_detail_parse", side_effect=fake_run_detail_parse):
            first, second = await asyncio.gather(
                detailed_api._parse_car_details_async(57021858),
                detailed_api._parse_car_details_async(57021858),
            )

        self.assertEqual(first, (None, False))
        self.assertEqual(second, (None, False))
        self.assertEqual(calls, 1)
        self.assertNotIn(57021858, detailed_api._inflight_detail_tasks)

    async def test_parse_car_details_uses_failure_cache_for_recent_banned_failure(self):
        calls = 0

        async def fake_run_detail_parse(car_id, shop_id=None):
            nonlocal calls
            calls += 1
            return None, True

        with mock.patch.object(detailed_api, "_run_detail_parse", side_effect=fake_run_detail_parse):
            first = await detailed_api._parse_car_details_async(57021858, shop_id=344884)
            second = await detailed_api._parse_car_details_async(57021858, shop_id=344884)

        self.assertEqual(first, (None, True))
        self.assertEqual(second, (None, True))
        self.assertEqual(calls, 1)

    async def test_parse_car_details_force_update_bypasses_failure_cache(self):
        calls = 0

        async def fake_run_detail_parse(car_id, shop_id=None):
            nonlocal calls
            calls += 1
            return None, True

        with mock.patch.object(detailed_api, "_run_detail_parse", side_effect=fake_run_detail_parse):
            await detailed_api._parse_car_details_async(57021858, shop_id=344884)
            await detailed_api._parse_car_details_async(57021858, shop_id=344884, force_update=True)

        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
