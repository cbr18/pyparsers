"""
Юнит-тесты для API сервера.
"""

import pytest
from fastapi.testclient import TestClient
from unittest import mock
from api_server import app
from api.dongchedi.parser import DongchediParser
from api.dongchedi.models.response import DongchediApiResponse, DongchediData
from api.dongchedi.models.car import DongchediCar


class TestApiServer:
    """Тесты для API сервера."""

    @pytest.fixture
    def client(self):
        """Фикстура для создания тестового клиента."""
        return TestClient(app)

    @pytest.fixture
    def mock_dongchedi_response(self):
        """Фикстура для создания мок-ответа от парсера dongchedi."""
        car = DongchediCar(
            uuid="test-uuid",
            car_id="12345",
            sku_id="12345",
            title="Test Car",
            car_name="Test Car Model",
            year=2020,
            car_year=2020,
            mileage=10000,
            car_mileage="10000 км",
            price="20.00",
            sh_price="20.00万",
            car_source_city_name="Beijing",
            city="Beijing",
            brand_name="Test Brand",
            series_name="Test Series",
            image="https://example.com/image.jpg",
            link="https://example.com/car/12345",
            shop_id="shop123",
            brand_id=1,
            series_id=2,
            tags='["tag1", "tag2"]',
            tags_v2='["tag3", "tag4"]',
            source="dongchedi",
            is_available=True,
            sort_number=1
        )

        data = DongchediData(
            has_more=True,
            search_sh_sku_info_list=[car],
            total=1
        )

        return DongchediApiResponse(
            data=data,
            message="Success",
            status=200
        )

    @mock.patch.object(DongchediParser, 'fetch_cars')
    def test_get_dongchedi_cars(self, mock_fetch_cars, client, mock_dongchedi_response):
        """Тест эндпоинта /cars/dongchedi."""
        # Настраиваем мок
        mock_fetch_cars.return_value = mock_dongchedi_response

        # Выполняем запрос
        response = client.get("/cars/dongchedi")

        # Проверяем результат
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 200
        assert data["message"] == "Success"
        assert data["data"]["total"] == 1
        assert data["data"]["has_more"] == True
        assert len(data["data"]["search_sh_sku_info_list"]) == 1

        car = data["data"]["search_sh_sku_info_list"][0]
        assert car["car_id"] == "12345"
        assert car["title"] == "Test Car"
        assert car["source"] == "dongchedi"

    @mock.patch.object(DongchediParser, 'fetch_cars_by_page')
    def test_get_dongchedi_cars_by_page(self, mock_fetch_cars_by_page, client, mock_dongchedi_response):
        """Тест эндпоинта /cars/dongchedi/page/{page}."""
        # Настраиваем мок
        mock_fetch_cars_by_page.return_value = mock_dongchedi_response

        # Выполняем запрос
        response = client.get("/cars/dongchedi/page/1")

        # Проверяем результат
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 200
        assert data["message"] == "Success"
        assert data["data"]["total"] == 1
        assert data["data"]["has_more"] == True
        assert data["data"]["current_page"] == 1
        assert len(data["data"]["search_sh_sku_info_list"]) == 1

        car = data["data"]["search_sh_sku_info_list"][0]
        assert car["car_id"] == "12345"
        assert car["title"] == "Test Car"
        assert car["source"] == "dongchedi"

    @mock.patch.object(DongchediParser, 'fetch_car_detail')
    def test_get_dongchedi_car_detail(self, mock_fetch_car_detail, client, mock_dongchedi_response):
        """Тест эндпоинта /cars/dongchedi/car/{car_id}."""
        # Настраиваем мок
        car = mock_dongchedi_response.data.search_sh_sku_info_list[0]
        mock_fetch_car_detail.return_value = (car, {"status": 200, "is_available": True})

        # Выполняем запрос
        response = client.get("/cars/dongchedi/car/12345")

        # Проверяем результат
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 200
        assert data["message"] == "Success"
        assert data["data"]["car_id"] == "12345"
        assert data["data"]["title"] == "Test Car"
        assert data["data"]["source"] == "dongchedi"

    @mock.patch.object(DongchediParser, 'fetch_car_detail')
    def test_get_dongchedi_car_detail_error(self, mock_fetch_car_detail, client):
        """Тест эндпоинта /cars/dongchedi/car/{car_id} с ошибкой."""
        # Настраиваем мок
        mock_fetch_car_detail.return_value = (None, {"status": 500, "error": "Test error", "is_available": False})

        # Выполняем запрос
        response = client.get("/cars/dongchedi/car/12345")

        # Проверяем результат
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 500
        assert "Ошибка при парсинге" in data["message"]
        assert data["data"]["car_id"] == "12345"
        assert data["data"]["is_available"] == False
        assert data["data"]["source"] == "dongchedi"
        assert data["data"]["error"] == "Test error"
