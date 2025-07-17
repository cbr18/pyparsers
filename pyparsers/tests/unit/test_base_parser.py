"""
Юнит-тесты для базового парсера.
"""

import pytest
from api.base_parser import BaseCarParser


class TestBaseParser:
    """Тесты для базового парсера."""

    class MockParser(BaseCarParser):
        """Мок-класс для тестирования BaseCarParser."""

        def fetch_cars(self, source=None):
            """Реализация абстрактного метода."""
            return {"source": source}

    def test_get_parser_name(self):
        """Тест метода get_parser_name."""
        parser = self.MockParser()
        assert parser.get_parser_name() == "MockParser"

    def test_fetch_cars_abstract(self):
        """Тест абстрактного метода fetch_cars."""
        parser = self.MockParser()
        result = parser.fetch_cars(source="test")
        assert result == {"source": "test"}

    def test_base_parser_is_abstract(self):
        """Тест, что BaseCarParser является абстрактным классом."""
        with pytest.raises(TypeError):
            BaseCarParser()
