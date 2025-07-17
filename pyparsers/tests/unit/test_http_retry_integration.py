"""
Интеграционные тесты для проверки взаимодействия HTTP-клиента с механизмом повторных попыток.
"""

import pytest
import asyncio
import aiohttp
import time
from unittest import mock
from api.http_client import HTTPClient
from api.retry import RetryStrategy, CircuitBreaker, CircuitState


class TestHTTPRetryIntegration:
    """Тесты для проверки интеграции HTTP-клиента с механизмом повторных попыток."""

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

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_request_with_retry_decorator(self, mock_request, http_client):
        """Тест использования декоратора async_retry в методе _request."""
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
        status, json_data, text = await http_client.get("/api/v1/test")

        # Проверяем результат
        assert status == 200
        assert json_data == {"key": "value"}
        assert text == '{"key": "value"}'

        # Проверяем, что запрос был выполнен дважды
        assert mock_request.call_count == 2

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_request_with_circuit_breaker(self, mock_request, http_client):
        """Тест взаимодействия HTTP-клиента с Circuit Breaker."""
        # Настраиваем мок для возврата ошибки
        mock_response_error = mock.MagicMock()
        mock_response_error.status = 500
        mock_response_error.text.return_value = asyncio.Future()
        mock_response_error.text.return_value.set_result("Server Error")
        mock_response_error.json.side_effect = aiohttp.ContentTypeError(None, None)

        # Настраиваем мок для возврата ошибки при каждом вызове
        mock_request.return_value.__aenter__.return_value = mock_response_error

        # Выполняем запрос несколько раз, чтобы активировать Circuit Breaker
        for _ in range(5):
            status, json_data, text = await http_client.get("/api/v1/test")
            assert status == 500

        # Проверяем, что Circuit Breaker перешел в состояние OPEN
        from api.retry import default_circuit_breaker
        endpoint = "GET:example.com"
        assert default_circuit_breaker.get_endpoint_state(endpoint)["state"] == CircuitState.OPEN

        # Сбрасываем состояние Circuit Breaker для следующих тестов
        default_circuit_breaker.endpoints[endpoint]["state"] = CircuitState.CLOSED
        default_circuit_breaker.endpoints[endpoint]["failures"] = 0

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_request_with_exception(self, mock_request, http_client):
        """Тест обработки исключений с использованием механизма повторных попыток."""
        # Настраиваем мок для возврата исключения при первом вызове
        mock_request.side_effect = [
            aiohttp.ClientError("Connection Error"),
            mock.MagicMock()
        ]

        # Настраиваем мок для второго вызова (успех)
        mock_response_success = mock.MagicMock()
        mock_response_success.status = 200
        mock_response_success.text.return_value = asyncio.Future()
        mock_response_success.text.return_value.set_result('{"key": "value"}')
        mock_response_success.json.return_value = asyncio.Future()
        mock_response_success.json.return_value.set_result({"key": "value"})

        # Настраиваем последовательность возвращаемых значений
        mock_request.return_value.__aenter__.return_value = mock_response_success

        # Выполняем запрос
        status, json_data, text = await http_client.get("/api/v1/test")

        # Проверяем результат
        assert status == 200
        assert json_data == {"key": "value"}
        assert text == '{"key": "value"}'

        # Проверяем, что запрос был выполнен дважды
        assert mock_request.call_count == 2

    @pytest.mark.asyncio
    @mock.patch("aiohttp.ClientSession.request")
    async def test_request_with_timeout(self, mock_request, http_client):
        """Тест обработки таймаутов с использованием механизма повторных попыток."""
        # Настраиваем мок для возврата исключения таймаута при первом вызове
        mock_request.side_effect = [
            asyncio.TimeoutError("Request timed out"),
            mock.MagicMock()
        ]

        # Настраиваем мок для второго вызова (успех)
        mock_response_success = mock.MagicMock()
        mock_response_success.status = 200
        mock_response_success.text.return_value = asyncio.Future()
        mock_response_success.text.return_value.set_result('{"key": "value"}')
        mock_response_success.json.return_value = asyncio.Future()
        mock_response_success.json.return_value.set_result({"key": "value"})

        # Настраиваем последовательность возвращаемых значений
        mock_request.return_value.__aenter__.return_value = mock_response_success

        # Выполняем запрос
        status, json_data, text = await http_client.get("/api/v1/test")

        # Проверяем результат
        assert status == 200
        assert json_data == {"key": "value"}
        assert text == '{"key": "value"}'

        # Проверяем, что запрос был выполнен дважды
        assert mock_request.call_count == 2
