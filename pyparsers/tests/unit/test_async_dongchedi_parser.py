"""
Юнит-тесты для асинхронного парсера dongchedi.
"""

import pytest
import json
import responses
import asyncio
from unittest import mock
from api.dongchedi.async_parser import AsyncDongchediParser
from api.dongchedi.models.response import DongchediApiResponse


class TestAsyncDongchediParser:
    """Тесты для асинхронного парсера dongchedi."""

    @pytest.fixture
    def async_dongchedi_parser(self):
        """Фикстура для создания экземпляра AsyncDongchediParser."""
        return AsyncDongchediParser()

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

    def test_build_url(self, async_dongchedi_parser):
        """Тест метода _build_url."""
        url = async_dongchedi_parser._build_url(1)
        assert "https://www.dongchedi.com/motor/pc/sh/sh_sku_list" in url
        assert "aid=1839" in url
        assert "page=1" in url
        assert "limit=80" in url
        assert "sort_type=4" in url

        # Тест с другим номером страницы
        url = async_dongchedi_parser._build_url(5)
        assert "page=5" in url

    @pytest.mark.asyncio
    @mock.patch("api.http_client.http_client.post")
    @mock.patch("api.http_client.http_client.get")
    async def test_async_fetch_cars(self, mock_get, mock_post, async_dongchedi_parser, mock_response_data):
        """Тест метода async_fetch_cars."""
        # Настраиваем мок для POST-запроса
        mock_post.return_value = (200, mock_response_data, json.dumps(mock_response_data))

        # Вызываем метод
        response = await async_dongchedi_parser.async_fetch_cars()

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

        # Проверяем, что был вызван метод post
        mock_post.assert_called_once()
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    @mock.patch("api.http_client.http_client.post")
    @mock.patch("api.http_client.http_client.get")
    async def test_async_fetch_cars_post_error(self, mock_get, mock_post, async_dongchedi_parser, mock_response_data):
        """Тест метода async_fetch_cars при ошибке POST-запроса."""
        # Настраиваем мок для POST-запроса с ошибкой
        mock_post.return_value = (500, {}, "Server Error")
        # Настраиваем мок для GET-запроса
        mock_get.return_value = (200, mock_response_data, json.dumps(mock_response_data))

        # Вызываем метод
        response = await async_dongchedi_parser.async_fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 200
        assert response.message == "Success"
        assert len(response.data.search_sh_sku_info_list) == 1

        # Проверяем, что были вызваны методы post и get
        mock_post.assert_called_once()
        mock_get.assert_called_once()

    @pytest.mark.asyncio
    @mock.patch("api.http_client.http_client.post")
    @mock.patch("api.http_client.http_client.get")
    async def test_async_fetch_cars_both_error(self, mock_get, mock_post, async_dongchedi_parser):
        """Тест метода async_fetch_cars при ошибке обоих запросов."""
        # Настраиваем моки с ошибками
        mock_post.return_value = (500, {}, "Server Error")
        mock_get.return_value = (500, {}, "Server Error")

        # Вызываем метод
        response = await async_dongchedi_parser.async_fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 500
        assert "Ошибка HTTP: 500" in response.message
        assert len(response.data.search_sh_sku_info_list) == 0

        # Проверяем, что были вызваны методы post и get
        mock_post.assert_called_once()
        mock_get.assert_called_once()

    @pytest.mark.asyncio
    @mock.patch("api.http_client.http_client.post")
    async def test_async_fetch_cars_exception(self, mock_post, async_dongchedi_parser):
        """Тест метода async_fetch_cars при исключении."""
        # Настраиваем мок для вызова исключения
        mock_post.side_effect = Exception("Test exception")

        # Вызываем метод
        response = await async_dongchedi_parser.async_fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 500
        assert "Ошибка при получении данных" in response.message
        assert len(response.data.search_sh_sku_info_list) == 0

    @pytest.mark.asyncio
    @mock.patch("api.http_client.http_client.post")
    async def test_async_fetch_cars_invalid_json(self, mock_post, async_dongchedi_parser):
        """Тест метода async_fetch_cars при некорректном JSON."""
        # Настраиваем мок для возврата некорректного JSON
        mock_post.return_value = (200, {}, "Invalid JSON")

        # Вызываем метод
        response = await async_dongchedi_parser.async_fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 500
        assert "Ошибка при получении данных" in response.message
        assert len(response.data.search_sh_sku_info_list) == 0

    @pytest.mark.asyncio
    @mock.patch("api.http_client.http_client.post")
    async def test_async_fetch_cars_empty_data(self, mock_post, async_dongchedi_parser):
        """Тест метода async_fetch_cars при пустых данных."""
        # Настраиваем мок для возврата пустых данных
        mock_post.return_value = (200, {"data": {}}, json.dumps({"data": {}}))

        # Вызываем метод
        response = await async_dongchedi_parser.async_fetch_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 404
        assert "не найдена или данные не соответствуют ожидаемому формату" in response.message
        assert len(response.data.search_sh_sku_info_list) == 0

    @pytest.mark.asyncio
    @mock.patch("api.http_client.http_client.post")
    async def test_process_car_data(self, mock_post, async_dongchedi_parser, mock_response_data):
        """Тест метода _process_car_data."""
        # Получаем тестовые данные о машинах
        car_data_list = mock_response_data["data"]["search_sh_sku_info_list"]

        # Вызываем метод
        cars = await async_dongchedi_parser._process_car_data(car_data_list)

        # Проверяем результат
        assert len(cars) == 1
        car = cars[0]
        assert car.car_id == "12345"
        assert car.title == "Test Car"
        assert car.year == 2020
        assert car.source == "dongchedi"

    @pytest.mark.asyncio
    async def test_process_single_car(self, async_dongchedi_parser):
        """Тест метода _process_single_car."""
        # Создаем тестовые данные о машине
        car_data = {
            "car_id": 12345,
            "sku_id": 12345,
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

        # Вызываем метод
        car = await async_dongchedi_parser._process_single_car(car_data)

        # Проверяем результат
        assert car is not None
        assert car.car_id == "12345"
        assert car.title == "Test Car"
        assert car.year == 2020
        assert car.source == "dongchedi"
        assert car.mileage == 10000
        assert car.city == "Beijing"
        assert car.is_available == True

    @pytest.mark.asyncio
    async def test_process_single_car_error(self, async_dongchedi_parser):
        """Тест метода _process_single_car при ошибке."""
        # Создаем некорректные данные о машине
        car_data = {
            "car_id": 12345,
            # Отсутствуют обязательные поля
        }

        # Вызываем метод
        car = await async_dongchedi_parser._process_single_car(car_data)

        # Проверяем результат
        assert car is None

    @pytest.mark.asyncio
    @mock.patch("api.dongchedi.async_parser.AsyncDongchediParser.async_fetch_cars_by_page")
    async def test_async_fetch_all_cars(self, mock_fetch_cars_by_page, async_dongchedi_parser):
        """Тест метода async_fetch_all_cars."""
        # Создаем тестовые данные для первой страницы
        car1 = mock.MagicMock()
        car1.dict.return_value = {"car_id": "1", "title": "Car 1", "source": "dongchedi"}

        # Создаем тестовые данные для второй страницы
        car2 = mock.MagicMock()
        car2.dict.return_value = {"car_id": "2", "title": "Car 2", "source": "dongchedi"}

        # Настраиваем мок для возврата данных с разных страниц
        response1 = mock.MagicMock()
        response1.data.search_sh_sku_info_list = [car1]
        response1.data.has_more = True

        response2 = mock.MagicMock()
        response2.data.search_sh_sku_info_list = [car2]
        response2.data.has_more = False

        mock_fetch_cars_by_page.side_effect = [response1, response2]

        # Вызываем метод
        response = await async_dongchedi_parser.async_fetch_all_cars()

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 200
        assert "Загружено 2 машин" in response.message
        assert len(response.data.search_sh_sku_info_list) == 2

        # Проверяем, что метод async_fetch_cars_by_page был вызван дважды
        assert mock_fetch_cars_by_page.call_count == 2

    @pytest.mark.asyncio
    @mock.patch("api.dongchedi.async_parser.AsyncDongchediParser.async_fetch_cars_by_page")
    async def test_async_fetch_incremental_cars(self, mock_fetch_cars_by_page, async_dongchedi_parser):
        """Тест метода async_fetch_incremental_cars."""
        # Создаем тестовые данные для существующих машин
        existing_cars = [
            {"car_id": "1", "title": "Car 1", "source": "dongchedi", "sort_number": 10},
            {"car_id": "2", "title": "Car 2", "source": "dongchedi", "sort_number": 9}
        ]

        # Создаем тестовые данные для новых машин
        car3 = mock.MagicMock()
        car3.dict.return_value = {"car_id": "3", "title": "Car 3", "source": "dongchedi"}

        car4 = mock.MagicMock()
        car4.dict.return_value = {"car_id": "4", "title": "Car 4", "source": "dongchedi"}

        car1 = mock.MagicMock()
        car1.dict.return_value = {"car_id": "1", "title": "Car 1", "source": "dongchedi"}

        # Настраиваем мок для возврата данных с разных страниц
        response1 = mock.MagicMock()
        response1.data.search_sh_sku_info_list = [car3, car4]
        response1.data.has_more = True

        response2 = mock.MagicMock()
        response2.data.search_sh_sku_info_list = [car1]  # Существующая машина
        response2.data.has_more = False

        mock_fetch_cars_by_page.side_effect = [response1, response2]

        # Вызываем метод
        response = await async_dongchedi_parser.async_fetch_incremental_cars(existing_cars)

        # Проверяем результат
        assert isinstance(response, DongchediApiResponse)
        assert response.status == 200
        assert "Найдено 2 новых машин" in response.message
        assert len(response.data.search_sh_sku_info_list) == 2

        # Проверяем, что метод async_fetch_cars_by_page был вызван дважды
        assert mock_fetch_cars_by_page.call_count == 2
