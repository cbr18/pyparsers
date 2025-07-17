"""
Юнит-тесты для асинхронного HTTP-клиента.
"""

import pytest
import aiohttp
import asyncio
import json
import responses
from unittest import mock
from api.http_client import HTTPClient


class TestHTTPClient:
    """Тесты для асинхронного HTTP-клиента."""

    @pytest.fixture
    def http_client(self):
        """Фикстура для создания экземпляра HTTPClient."""
        client = HTTPClient(
            base_url="https://example.com",
            headers={"User-Agent": "Test-Agent"},
            timeout=5.0,
            max_retries=2,
            retry_delay=0.1
        )
        yield client
        # Закрываем сессию после теста
        loop = asyncio.get_event_loop()
        if client._session and not client._session.closed:
            loop.run_until_complete(client.close())

    def test_build_url(self, http_client):
        """Тест метода _build_url."""
        # Тест с базовым URL
        url = http_client._build_url("/api/v1/test")
        assert url == "https://example.com/api/v1/test"

        # Тест с параметрами
        url = http_client._build_url("/api/v1/test", {"param1": "value1", "param2": "value2"})
        assert "https://example.com/api/v1/test" in url
        assert "param1=value1" in url
        assert "param2=value2" in url

        # Тест с полным URL
        url = http_client._build_url("https://another.com/api/v1/test")
        assert url == "https://another.com/api/v1/test"

        # Тест с полным URL и параметрами
        url = http_client._build_url("https://another.com/api/v1/test", {"param1": "value1"})
        assert "https://another.com/api/v1/test" in url
        assert "param1=value1" in url

    @pytest.mark.asyncio
    async def test_get_session(self, http_client):
        """Тест метода _get_session."""
        session = await http_client._get_session()
        assert isinstance(session, aiohttp.ClientSession)
        assert not session.closed

        # Проверяем, что повторный вызов возвращает ту же сессию
        session2 = await http_client._get_session()
        assert session is session2

    @pytest.mark.asyncio
    async def test_close(self, http_client):
        """Тест метода close."""
        session = await http_client._get_session()
        assert not session.closed

        await http_client.close()
        assert session.closed

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_request_success(self, mock_request, http_client):
        """Тест успешного выполнения запроса."""
        # Настраиваем мок
        mock_response = mock.MagicMock()
        mock_response.status = 200
        mock_response.text.return_value = asyncio.Future()
        mock_response.text.return_value.set_result('{"key": "value"}')
        mock_response.json.return_value = asyncio.Future()
        mock_response.json.return_value.set_result({"key": "value"})

        mock_request.return_value.__aenter__.return_value = mock_response

        # Выполняем запрос
        status, json_data, text = await http_client._request("GET", "/api/v1/test")

        # Проверяем результат
        assert status == 200
        assert json_data == {"key": "value"}
        assert text == '{"key": "value"}'

        # Проверяем, что запрос был выполнен с правильными параметрами
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "GET"
        assert kwargs["url"] == "https://example.com/api/v1/test"

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_request_server_error_retry(self, mock_request, http_client):
        """Тест повторных попыток при серверной ошибке."""
        # Настраиваем мок для первого вызова (ошибка 500)
        mock_response_error = mock.MagicMock()
        mock_response_error.status = 500
        mock_response_error.text.return_value = asyncio.Future()
        mock_response_error.text.return_value.set_result("Server Error")
        mock_response_error.json.side_effect = aiohttp.ContentTypeError(None, None)

        # Настраиваем мок для второго вызова (успех)
        mock_response_success = mock.MagicMock()
        mock_response_success.status = 200
        mock_response_success.text.return_value = asyncio.Future()
        mock_response_success.text.return_value.set_result('{"key": "value"}')
        mock_response_success.json.return_value = asyncio.Future()
        mock_response_success.json.return_value.set_result({"key": "value"})

        # Настраиваем последовательность возвращаемых значений
        mock_request.return_value.__aenter__.side_effect = [
            mock_response_error,
            mock_response_success
        ]

        # Выполняем запрос
        status, json_data, text = await http_client._request("GET", "/api/v1/test")

        # Проверяем результат
        assert status == 200
        assert json_data == {"key": "value"}
        assert text == '{"key": "value"}'

        # Проверяем, что запрос был выполнен дважды
        assert mock_request.call_count == 2

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_request_client_error(self, mock_request, http_client):
        """Тест обработки клиентской ошибки."""
        # Настраиваем мок для вызова с клиентской ошибкой
        mock_request.side_effect = aiohttp.ClientError("Client Error")

        # Выполняем запрос
        status, json_data, text = await http_client._request("GET", "/api/v1/test")

        # Проверяем результат
        assert status == 0
        assert json_data == {}
        assert "Client Error" in text

        # Проверяем, что было выполнено максимальное количество попыток
        assert mock_request.call_count == http_client.max_retries

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_get(self, mock_request, http_client):
        """Тест метода get."""
        # Настраиваем мок
        mock_response = mock.MagicMock()
        mock_response.status = 200
        mock_response.text.return_value = asyncio.Future()
        mock_response.text.return_value.set_result('{"key": "value"}')
        mock_response.json.return_value = asyncio.Future()
        mock_response.json.return_value.set_result({"key": "value"})

        mock_request.return_value.__aenter__.return_value = mock_response

        # Выполняем запрос
        status, json_data, text = await http_client.get(
            "/api/v1/test",
            params={"param": "value"},
            headers={"Custom-Header": "Value"}
        )

        # Проверяем результат
        assert status == 200
        assert json_data == {"key": "value"}
        assert text == '{"key": "value"}'

        # Проверяем, что запрос был выполнен с правильными параметрами
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "GET"
        assert "param=value" in kwargs["url"]
        assert kwargs["headers"]["Custom-Header"] == "Value"

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_post(self, mock_request, http_client):
        """Тест метода post."""
        # Настраиваем мок
        mock_response = mock.MagicMock()
        mock_response.status = 201
        mock_response.text.return_value = asyncio.Future()
        mock_response.text.return_value.set_result('{"id": 1}')
        mock_response.json.return_value = asyncio.Future()
        mock_response.json.return_value.set_result({"id": 1})

        mock_request.return_value.__aenter__.return_value = mock_response

        # Выполняем запрос
        status, json_data, text = await http_client.post(
            "/api/v1/test",
            json_data={"name": "Test"},
            headers={"Custom-Header": "Value"}
        )

        # Проверяем результат
        assert status == 201
        assert json_data == {"id": 1}
        assert text == '{"id": 1}'

        # Проверяем, что запрос был выполнен с правильными параметрами
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["json"] == {"name": "Test"}
        assert kwargs["headers"]["Custom-Header"] == "Value"

    @responses.activate
    def test_sync_get(self, http_client):
        """Тест метода sync_get."""
        # Настраиваем мок
        responses.add(
            responses.GET,
            "https://example.com/api/v1/test",
            json={"key": "value"},
            status=200
        )

        # Выполняем запрос
        response = http_client.sync_get("/api/v1/test")

        # Проверяем результат
        assert response.status_code == 200
        assert response.json() == {"key": "value"}

    @responses.activate
    def test_sync_post(self, http_client):
        """Тест метода sync_post."""
        # Настраиваем мок
        responses.add(
            responses.POST,
            "https://example.com/api/v1/test",
            json={"id": 1},
            status=201
        )

        # Выполняем запрос
        response = http_client.sync_post(
            "/api/v1/test",
            json={"name": "Test"}
        )

        # Проверяем результат
        assert response.status_code == 201
        assert response.json() == {"id": 1}

    @responses.activate
    def test_sync_get_retry(self, http_client):
        """Тест повторных попыток в методе sync_get."""
        # Настраиваем моки для последовательности ответов
        responses.add(
            responses.GET,
            "https://example.com/api/v1/test",
            json={"error": "Server Error"},
            status=500
        )
        responses.add(
            responses.GET,
            "https://example.com/api/v1/test",
            json={"key": "value"},
            status=200
        )

        # Выполняем запрос
        response = http_client.sync_get("/api/v1/test")

        # Проверяем результат
        assert response.status_code == 200
        assert response.json() == {"key": "value"}
        assert len(responses.calls) == 2
