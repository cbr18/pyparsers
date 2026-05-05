import unittest
from unittest import mock
import sys

# Mocking modules that are not installed
mock_selenium = mock.Mock()
mock_webdriver = mock.Mock()
mock_selenium.webdriver = mock_webdriver
sys.modules["selenium"] = mock_selenium
sys.modules["selenium.webdriver"] = mock_webdriver
sys.modules["selenium.webdriver.common.by"] = mock.Mock()
sys.modules["selenium.webdriver.support.ui"] = mock.Mock()
sys.modules["selenium.webdriver.support"] = mock.Mock()
sys.modules["selenium.webdriver.chrome.options"] = mock.Mock()
sys.modules["selenium.webdriver.chrome.service"] = mock.Mock()
sys.modules["selenium.common.exceptions"] = mock.Mock()

from api.dongchedi.parser import DongchediParser

class DongchediParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = DongchediParser()

    @mock.patch("bs4.BeautifulSoup")
    def test_fetch_car_specifications_selenium_fallback(self, mock_bs):
        # Mocking the selenium flow
        mock_driver = mock.Mock()
        mock_webdriver.Chrome.return_value = mock_driver
        mock_driver.page_source = "<html><div class='table_row__yVX1h'><label class='cell_label__ZtXlw'>最大马力(Ps)</label><div class='cell_normal__37nRi'>184</div></div></html>"
        
        # Mock BeautifulSoup to return a row
        mock_soup = mock.Mock()
        mock_bs.return_value = mock_soup
        
        mock_row = mock.Mock()
        mock_label = mock.Mock()
        mock_label.get_text.return_value = "最大马力(Ps)"
        mock_value = mock.Mock()
        mock_value.get_text.return_value = "184"
        
        mock_row.find.side_effect = lambda tag, class_: mock_label if tag == "label" else mock_value
        mock_soup.find_all.return_value = [mock_row]
        
        # We need to mock sleep to speed up tests
        with mock.patch("time.sleep"):
            specs, meta = self.parser.fetch_car_specifications("12345")
        
        self.assertEqual(specs.get("power"), 184)
        self.assertEqual(meta["status"], 200)

    @mock.patch("requests.get")
    def test_fetch_specs_via_json_api_success(self, mock_get):
        # Mocking JSON API response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 0,
            "data": {
                "config_data": [
                    {
                        "items": [
                            {
                                "name": "最大马力(Ps)",
                                "values": [{"value": "150"}]
                            },
                            {
                                "name": "排量(mL)",
                                "values": [{"value": "1998"}]
                            }
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        specs = self.parser._fetch_specs_via_json_api("car_123", "series_456")
        
        self.assertEqual(specs.get("power"), 150)
        self.assertEqual(specs.get("engine_volume_ml"), 1998)

    @mock.patch("requests.get")
    def test_fetch_specs_via_next_data_success(self, mock_get):
        # Mocking __NEXT_DATA__ response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><script id="__NEXT_DATA__">{"props": {"pageProps": {"config_data": [{"items": [{"name": "最大功率(kW)", "values": [{"value": "110"}]}]}]}}}</script></html>'
        mock_get.return_value = mock_response
        
        specs = self.parser._fetch_specs_via_next_data("car_123")
        
        # 110 kW -> ~150 Ps
        self.assertEqual(specs.get("power"), 150)

    @mock.patch.object(DongchediParser, "_fetch_specs_via_json_api")
    def test_fetch_car_specifications_precedence(self, mock_json_api):
        # Mocking JSON API success
        mock_json_api.return_value = {"power": 150, "engine_volume_ml": 2000}
        
        specs, meta = self.parser.fetch_car_specifications("car_123", series_id="series_456")
        
        self.assertEqual(specs.get("power"), 150)
        self.assertEqual(meta["method"], "json_api")
        mock_json_api.assert_called_once()

if __name__ == "__main__":
    unittest.main()
