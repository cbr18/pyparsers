"""
Юнит-тесты для модуля logging_utils.
"""

import pytest
import json
import logging
import asyncio
from unittest import mock
from api.logging_utils import (
    StructuredLogger,
    ErrorHandler,
    ErrorCategory,
    log_function,
    log_async_function
)


class TestStructuredLogger:
    """Тесты для класса StructuredLogger."""

    def test_init(self):
        """Тест инициализации StructuredLogger."""
        logger = StructuredLogger(
            name="test_logger",
            level=logging.DEBUG,
            add_console_handler=True,
            add_file_handler=False,
            json_format=True
        )

        assert logger.name == "test_logger"
        assert logger.level == logging.DEBUG
        assert logger.json_format is True
        assert len(logger.logger.handlers) == 1

    @mock.patch("logging.Logger.debug")
    def test_debug(self, mock_debug):
        """Тест метода debug."""
        logger = StructuredLogger(name="test_logger", json_format=True)

        logger.debug(
            message="Test debug message",
            error=ValueError("Test error"),
            error_category=ErrorCategory.VALIDATION_ERROR,
            context={"key": "value"}
        )

        # Проверяем, что метод debug был вызван
        mock_debug.assert_called_once()

        # Проверяем, что сообщение было отформатировано как JSON
        args, kwargs = mock_debug.call_args
        log_message = args[0]
        log_data = json.loads(log_message)

        assert log_data["level"] == "DEBUG"
        assert log_data["message"] == "Test debug message"
        assert log_data["logger"] == "test_logger"
        assert log_data["error"]["type"] == "ValueError"
        assert log_data["error"]["message"] == "Test error"
        assert log_data["error"]["category"] == "validation_error"
        assert log_data["context"] == {"key": "value"}

    @mock.patch("logging.Logger.info")
    def test_info(self, mock_info):
        """Тест метода info."""
        logger = StructuredLogger(name="test_logger", json_format=True)

        logger.info(
            message="Test info message",
            context={"key": "value"}
        )

        # Проверяем, что метод info был вызван
        mock_info.assert_called_once()

        # Проверяем, что сообщение было отформатировано как JSON
        args, kwargs = mock_info.call_args
        log_message = args[0]
        log_data = json.loads(log_message)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test info message"
        assert log_data["logger"] == "test_logger"
        assert log_data["context"] == {"key": "value"}

    @mock.patch("logging.Logger.warning")
    def test_warning(self, mock_warning):
        """Тест метода warning."""
        logger = StructuredLogger(name="test_logger", json_format=True)

        logger.warning(
            message="Test warning message",
            error=ValueError("Test error"),
            error_category=ErrorCategory.VALIDATION_ERROR,
            context={"key": "value"}
        )

        # Проверяем, что метод warning был вызван
        mock_warning.assert_called_once()

        # Проверяем, что сообщение было отформатировано как JSON
        args, kwargs = mock_warning.call_args
        log_message = args[0]
        log_data = json.loads(log_message)

        assert log_data["level"] == "WARNING"
        assert log_data["message"] == "Test warning message"
        assert log_data["logger"] == "test_logger"
        assert log_data["error"]["type"] == "ValueError"
        assert log_data["error"]["message"] == "Test error"
        assert log_data["error"]["category"] == "validation_error"
        assert log_data["context"] == {"key": "value"}

    @mock.patch("logging.Logger.error")
    def test_error(self, mock_error):
        """Тест метода error."""
        logger = StructuredLogger(name="test_logger", json_format=True)

        logger.error(
            message="Test error message",
            error=ValueError("Test error"),
            error_category=ErrorCategory.VALIDATION_ERROR,
            context={"key": "value"}
        )

        # Проверяем, что метод error был вызван
        mock_error.assert_called_once()

        # Проверяем, что сообщение было отформатировано как JSON
        args, kwargs = mock_error.call_args
        log_message = args[0]
        log_data = json.loads(log_message)

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Test error message"
        assert log_data["logger"] == "test_logger"
        assert log_data["error"]["type"] == "ValueError"
        assert log_data["error"]["message"] == "Test error"
        assert log_data["error"]["category"] == "validation_error"
        assert log_data["context"] == {"key": "value"}

    @mock.patch("logging.Logger.critical")
    def test_critical(self, mock_critical):
        """Тест метода critical."""
        logger = StructuredLogger(name="test_logger", json_format=True)

        logger.critical(
            message="Test critical message",
            error=ValueError("Test error"),
            error_category=ErrorCategory.VALIDATION_ERROR,
            context={"key": "value"}
        )

        # Проверяем, что метод critical был вызван
        mock_critical.assert_called_once()

        # Проверяем, что сообщение было отформатировано как JSON
        args, kwargs = mock_critical.call_args
        log_message = args[0]
        log_data = json.loads(log_message)

        assert log_data["level"] == "CRITICAL"
        assert log_data["message"] == "Test critical message"
        assert log_data["logger"] == "test_logger"
        assert log_data["error"]["type"] == "ValueError"
        assert log_data["error"]["message"] == "Test error"
        assert log_data["error"]["category"] == "validation_error"
        assert log_data["context"] == {"key": "value"}

    def test_format_message_no_json(self):
        """Тест метода _format_message без JSON."""
        logger = StructuredLogger(name="test_logger", json_format=False)

        # Форматируем сообщение без ошибки
        message = logger._format_message(
            level="INFO",
            message="Test message"
        )

        assert message == "Test message"

        # Форматируем сообщение с ошибкой
        message = logger._format_message(
            level="ERROR",
            message="Test message",
            error=ValueError("Test error")
        )

        assert message == "Test message: Test error"


class TestErrorHandler:
    """Тесты для класса ErrorHandler."""

    def test_init(self):
        """Тест инициализации ErrorHandler."""
        logger = StructuredLogger(name="test_logger")
        handler = ErrorHandler(logger=logger)

        assert handler.logger == logger
        assert isinstance(handler.error_categories, dict)
        assert isinstance(handler.error_handlers, dict)

    def test_categorize_error(self):
        """Тест метода categorize_error."""
        handler = ErrorHandler()

        # Проверяем категоризацию известных ошибок
        assert handler.categorize_error(ConnectionError()) == ErrorCategory.CONNECTION_ERROR
        assert handler.categorize_error(TimeoutError()) == ErrorCategory.TIMEOUT_ERROR
        assert handler.categorize_error(json.JSONDecodeError("Test error", "", 0)) == ErrorCategory.JSON_PARSING_ERROR

        # Проверяем категоризацию неизвестных ошибок
        assert handler.categorize_error(KeyError()) == ErrorCategory.UNKNOWN_ERROR

    def test_register_error_handler(self):
        """Тест метода register_error_handler."""
        handler = ErrorHandler()

        # Регистрируем обработчик для категории ошибок
        mock_handler = mock.Mock()
        handler.register_error_handler(ErrorCategory.VALIDATION_ERROR, mock_handler)

        assert handler.error_handlers[ErrorCategory.VALIDATION_ERROR] == mock_handler

    @mock.patch.object(StructuredLogger, "error")
    def test_handle_error(self, mock_error):
        """Тест метода handle_error."""
        logger = StructuredLogger(name="test_logger")
        handler = ErrorHandler(logger=logger)

        # Регистрируем обработчик для категории ошибок
        mock_handler_func = mock.Mock()
        handler.register_error_handler(ErrorCategory.VALIDATION_ERROR, mock_handler_func)

        # Обрабатываем ошибку с зарегистрированным обработчиком
        error = ValueError("Test error")
        handler.error_categories["ValueError"] = ErrorCategory.VALIDATION_ERROR

        handler.handle_error(
            error=error,
            context={"key": "value"}
        )

        # Проверяем, что метод error был вызван
        mock_error.assert_called_once()

        # Проверяем, что обработчик был вызван
        mock_handler_func.assert_called_once_with(error, {"key": "value"})

        # Обрабатываем ошибку без зарегистрированного обработчика
        mock_error.reset_mock()
        mock_handler_func.reset_mock()

        error = KeyError("Test error")

        handler.handle_error(
            error=error,
            context={"key": "value"}
        )

        # Проверяем, что метод error был вызван
        mock_error.assert_called_once()

        # Проверяем, что обработчик не был вызван
        mock_handler_func.assert_not_called()


class TestLogFunctionDecorator:
    """Тесты для декоратора log_function."""

    @mock.patch.object(StructuredLogger, "debug")
    def test_log_function(self, mock_debug):
        """Тест декоратора log_function."""
        logger = StructuredLogger(name="test_logger")

        @log_function(logger=logger)
        def test_func(arg1, arg2=None):
            return arg1 + (arg2 or 0)

        # Вызываем функцию
        result = test_func(1, arg2=2)

        # Проверяем результат
        assert result == 3

        # Проверяем, что метод debug был вызван дважды
        assert mock_debug.call_count == 2

        # Проверяем первый вызов (начало выполнения функции)
        args, kwargs = mock_debug.call_args_list[0]
        assert args[0] == "Calling test_func"
        assert "args" in kwargs["context"]
        assert "kwargs" in kwargs["context"]

        # Проверяем второй вызов (конец выполнения функции)
        args, kwargs = mock_debug.call_args_list[1]
        assert args[0] == "Called test_func"
        assert "elapsed" in kwargs["context"]

    @mock.patch.object(StructuredLogger, "debug")
    @mock.patch.object(ErrorHandler, "handle_error")
    def test_log_function_with_error(self, mock_handle_error, mock_debug):
        """Тест декоратора log_function при возникновении ошибки."""
        logger = StructuredLogger(name="test_logger")
        error_handler = ErrorHandler(logger=logger)

        @log_function(logger=logger, error_handler=error_handler)
        def test_func():
            raise ValueError("Test error")

        # Вызываем функцию
        with pytest.raises(ValueError):
            test_func()

        # Проверяем, что метод debug был вызван один раз
        assert mock_debug.call_count == 1

        # Проверяем вызов (начало выполнения функции)
        args, kwargs = mock_debug.call_args
        assert args[0] == "Calling test_func"

        # Проверяем, что метод handle_error был вызван
        mock_handle_error.assert_called_once()

        # Проверяем аргументы вызова
        args, kwargs = mock_handle_error.call_args
        assert isinstance(args[0], ValueError)
        assert args[0].args[0] == "Test error"
        assert "function" in kwargs["context"]
        assert "args" in kwargs["context"]
        assert "kwargs" in kwargs["context"]
        assert "elapsed" in kwargs["context"]


class TestLogAsyncFunctionDecorator:
    """Тесты для декоратора log_async_function."""

    @pytest.mark.asyncio
    @mock.patch.object(StructuredLogger, "debug")
    async def test_log_async_function(self, mock_debug):
        """Тест декоратора log_async_function."""
        logger = StructuredLogger(name="test_logger")

        @log_async_function(logger=logger)
        async def test_func(arg1, arg2=None):
            await asyncio.sleep(0.1)
            return arg1 + (arg2 or 0)

        # Вызываем функцию
        result = await test_func(1, arg2=2)

        # Проверяем результат
        assert result == 3

        # Проверяем, что метод debug был вызван дважды
        assert mock_debug.call_count == 2

        # Проверяем первый вызов (начало выполнения функции)
        args, kwargs = mock_debug.call_args_list[0]
        assert args[0] == "Calling test_func"
        assert "args" in kwargs["context"]
        assert "kwargs" in kwargs["context"]

        # Проверяем второй вызов (конец выполнения функции)
        args, kwargs = mock_debug.call_args_list[1]
        assert args[0] == "Called test_func"
        assert "elapsed" in kwargs["context"]

    @pytest.mark.asyncio
    @mock.patch.object(StructuredLogger, "debug")
    @mock.patch.object(ErrorHandler, "handle_error")
    async def test_log_async_function_with_error(self, mock_handle_error, mock_debug):
        """Тест декоратора log_async_function при возникновении ошибки."""
        logger = StructuredLogger(name="test_logger")
        error_handler = ErrorHandler(logger=logger)

        @log_async_function(logger=logger, error_handler=error_handler)
        async def test_func():
            await asyncio.sleep(0.1)
            raise ValueError("Test error")

        # Вызываем функцию
        with pytest.raises(ValueError):
            await test_func()

        # Проверяем, что метод debug был вызван один раз
        assert mock_debug.call_count == 1

        # Проверяем вызов (начало выполнения функции)
        args, kwargs = mock_debug.call_args
        assert args[0] == "Calling test_func"

        # Проверяем, что метод handle_error был вызван
        mock_handle_error.assert_called_once()

        # Проверяем аргументы вызова
        args, kwargs = mock_handle_error.call_args
        assert isinstance(args[0], ValueError)
        assert args[0].args[0] == "Test error"
        assert "function" in kwargs["context"]
        assert "args" in kwargs["context"]
        assert "kwargs" in kwargs["context"]
        assert "elapsed" in kwargs["context"]
