from .parser import Che168Parser
from .detailed_parser_api import Che168DetailedParserAPI as Che168DetailedParser

try:
    from .detailed_api import router as detailed_router
except Exception:  # pragma: no cover - optional during lightweight imports/tests
    detailed_router = None

__all__ = ['Che168Parser', 'Che168DetailedParser', 'detailed_router'] 
