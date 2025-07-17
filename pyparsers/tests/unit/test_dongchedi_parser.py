"""
Юнит-тесты для парсера dongchedi.
"""

import pytest
import json
import responses
from api.dongchedi.parser import DongchediParser
from api.dongchedi.models.response import DongchediApiResponse


class TestDongchediParser:
    """Тесты для парсера dongchedi."""

    @pytest.fixture
    def dongchedi_parser(self):
        """Фикстура для создания экземпляра DongchediParser."""
        return DongchediParser()

    @pytest.fixture
    def mock_response_data(self):
        """Фикстура для создания тестовых данных ответа API."""
        return {
            "data": {
                "has_more": True,
                "search_sh_sku_info_list": [
                    {
                        "car_id": "12345",
                        "sku_id": "12345",
                        "title": "Test Car",
                        "car_name": "Test Car Model",
                        "car_year": 2020,
                        "car_mileage": "10000 км",
                        "sh_price": "20.00万",
                        "car_source_city_name": "Beijing",
                        "brand_name": "Test Brand",
                        "series_name": "Test Series",
                        "image": "https://example.com/image.jpg",
                        "link": "https://example.com/car/12345",
                        "shop_id": "shop123",
                        "brand_id": 1,
                        "series_id": 2,
                        "tags": ["tag1", "tag2"],
                        "tags_v2": ["tag3", "tag4"],
                    }
                ],
                "total": 1
            },
            "message": "Success",
            "status": 200
        }

    def test_build_url(self, dongchedi_parser):
        """Тест метода _build_url."""
        url = dongchedi_parser._build_url(1)
        assert "https://www.dongchedi.com/motor/pc/sh/sh_sku_list" in url
        assert "aid=1839" in url
        assert "page=1" in url
        assert "limit=80" in url
        assert "sort_type=4" in url

        # Тест с другим номером страницы
        url = dongchedi_parser._build_url(5)
        assert "page=5" in url

    @responses.activate
    def test_fetch_cars(self, dongchedi_parser, mock_response_data):
        """Тест метода fetch_cars."""
        # Мокаем HTTP-запрос
        url = dongchedi_parser._build_url(1)
        responses.add(
            responses.GET,
            url,
            json=mock_response_data,
            status=200
        )
        responses.add(
            responses.POST,
            url,
            json=mock_response_data,
            status=200
        )

        # Вызываем метод
        response = dongchedi_parser.fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 200
        assert response.message == "Success"
        assert response.data.has_more == True
        assert response.data.total == 1
        assert len(response.data.search_sh_sku_info_list) == 1

        car = response.data.search_sh_sku_info_list[0]
        assert car.car_id == "12345"
        assert car.title == "Test Car"
        assert car.year == 2020
        assert car.source == "dongchedi"

    @responses.activate
    def test_fetch_cars_by_page(self, dongchedi_parser, mock_response_data):
        """Тест метода fetch_cars_by_page."""
        # Мокаем HTTP-запрос для разных страниц
        for page in range(1, 4):
            url = dongchedi_parser._build_url(page)
            # Модифицируем данные для разных страниц
            page_data = mock_response_data.copy()
            page_data["data"]["search_sh_sku_info_list"][0]["car_id"] = f"12345-{page}"
            page_data["data"]["search_sh_sku_info_list"][0]["title"] = f"Test Car {page}"

            responses.add(
                responses.GET,
                url,
                json=page_data,
                status=200
            )
            responses.add(
                responses.POST,
                url,
                json=page_data,
                status=200
            )

        # Вызываем метод для разных страниц
        for page in range(1, 4):
            response = dongchedi_parser.fetch_cars_by_page(page)

            # Проверяем результат
            assert isinstance(response, DongchediApiResponse)
            assert response.status == 200
            assert response.message == "Success"
            assert len(response.data.search_sh_sku_info_list) == 1

            car = response.data.search_sh_sku_info_list[0]
            assert car.car_id == f"12345-{page}"
            assert car.title == f"Test Car {page}"
            assert car.source == "dongchedi"

    @responses.activate
    def test_fetch_cars_error_handling(self, dongchedi_parser):
        """Тест обработки ошибок в методе fetch_cars."""
        # Мокаем HTTP-запрос с ошибкой
        url = dongchedi_parser._build_url(1)
        responses.add(
            responses.GET,
            url,
            json={"error": "Internal Server Error"},
            status=500
        )
        responses.add(
            responses.POST,
            url,
            json={"error": "Internal Server Error"},
            status=500
        )

        # Вызываем метод
        response = dongchedi_parser.fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 500
        assert "Ошибка при получении данных" in response.message
        assert len(response.data.search_sh_sku_info_list) == 0

    @responses.activate
    def test_fetch_cars_invalid_json(self, dongchedi_parser):
        """Тест обработки некорректного JSON в ответе API."""
        # Мокаем HTTP-запрос с некорректным JSON
        url = dongchedi_parser._build_url(1)
        responses.add(
            responses.GET,
            url,
            body="Invalid JSON",
            status=200
        )
        responses.add(
            responses.POST,
            url,
            body="Invalid JSON",
            status=200
        )

        # Вызываем метод
        response = dongchedi_parser.fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 500
        assert "Ошибка при получении данных" in response.message
        assert len(response.data.search_sh_sku_info_list) == 0

    @responses.activate
    def test_fetch_cars_missing_fields(self, dongchedi_parser):
        """Тест обработки отсутствующих полей в ответе API."""
        # Мокаем HTTP-запрос с отсутствующими полями
        url = dongchedi_parser._build_url(1)
        responses.add(
            responses.GET,
            url,
            json={"data": {}},
            status=200
        )
        responses.add(
            responses.POST,
            url,
            json={"data": {}},
            status=200
        )

        # Вызываем метод
        response = dongchedi_parser.fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 404
        assert "не найдена или данные не соответствуют ожидаемому формату" in response.message
        assert len(response.data.search_sh_sku_info_list) == 0
