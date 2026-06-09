import ipaddress
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pyparsers"))

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")

import async_api_server


class IPWhitelistMiddlewareTests(unittest.TestCase):
    def test_forbidden_response_includes_detected_client_ip(self):
        app = fastapi.FastAPI()
        app.add_middleware(async_api_server.IPWhitelistMiddleware, public_paths={"/health"})

        @app.get("/private")
        async def private():
            return {"ok": True}

        allowed_ips = [ipaddress.ip_address("192.0.2.10")]
        with patch.object(async_api_server, "ALLOWED_IPS", allowed_ips):
            response = testclient.TestClient(app).get(
                "/private",
                headers={"X-Forwarded-For": "10.20.30.40, 172.18.0.1"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "data": None,
                "message": "Access denied: IP not in whitelist",
                "client_ip": "10.20.30.40",
                "status": 403,
            },
        )


if __name__ == "__main__":
    unittest.main()
