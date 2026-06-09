import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pyparsers"))

import metrics


class MetricsTests(unittest.TestCase):
    def test_render_metrics_includes_counter_labels(self):
        metrics.REQUESTS_TOTAL.inc(source="test-source", method="GET", path="/tasks/{task_id}", status="200")

        rendered = metrics.render_metrics()

        self.assertIn("# TYPE pyparsers_http_requests_total counter", rendered)
        self.assertIn(
            'pyparsers_http_requests_total{method="GET",path="/tasks/{task_id}",source="test-source",status="200"}',
            rendered,
        )

    def test_normalized_route_prefers_route_pattern(self):
        request = SimpleNamespace(
            scope={"route": SimpleNamespace(path="/tasks/{task_id}")},
            url=SimpleNamespace(path="/tasks/abc"),
        )

        self.assertEqual(metrics.normalized_route(request), "/tasks/{task_id}")

    def test_normalized_route_falls_back_to_request_path(self):
        request = SimpleNamespace(scope={}, url=SimpleNamespace(path="/metrics"))

        self.assertEqual(metrics.normalized_route(request), "/metrics")

    def test_task_inventory_resets_previous_source_values(self):
        metrics.TASKS_ACTIVE.set(1, source="inventory-test", task_type="full", status="running", stage="listing")

        metrics.refresh_task_inventory("inventory-test", [], results_cached=0, queue_size=0)
        rendered = metrics.render_metrics()

        self.assertIn(
            'pyparsers_tasks_active{source="inventory-test",stage="listing",status="running",task_type="full"} 0',
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
