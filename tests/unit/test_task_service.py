import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pyparsers"))

from models import TaskCreateRequest, TaskStage, TaskStatus, TaskType
from task_service import (
    BatchDeliveryState,
    TaskRunResult,
    TaskService,
    _append_unique_listing,
    _build_batch_delivery_state,
    _delivery_summary,
    _flush_listing_batch,
    _normalize_detailed_items,
    _post_parser_batch,
    build_task_service,
)


class TaskServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        if hasattr(self, "service"):
            await self.service.shutdown()

    async def test_task_transitions_from_queued_to_succeeded_with_result(self):
        async def full_runner(context, parameters):
            await context.set_stage(TaskStage.LISTING, message="listing", progress_current=1, progress_total=3, progress_unit="page")
            await context.update(items_found=10)
            await context.set_stage(TaskStage.FINALIZING, message="finalizing")
            return TaskRunResult(result=[{"car_id": 1}], summary={"pages_scanned": 1, "items_found": 10})

        self.service = TaskService(source="dongchedi", runners={TaskType.FULL: full_runner})
        await self.service.startup()

        task = self.service.create_task(TaskCreateRequest(task_type=TaskType.FULL))
        self.assertEqual(task.status, TaskStatus.QUEUED)

        await asyncio.wait_for(self.service._queue.join(), timeout=2)

        snapshot = self.service.get_task(task.id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.status, TaskStatus.SUCCEEDED)
        self.assertEqual(snapshot.stage, TaskStage.COMPLETED)
        self.assertTrue(snapshot.result_available)
        self.assertEqual(snapshot.items_found, 10)
        self.assertEqual(snapshot.result_summary["pages_scanned"], 1)

        result = self.service.get_task_result(task.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.result, [{"car_id": 1}])
        self.assertIsNotNone(result.task.result_fetched_at)

    async def test_running_task_can_be_cancelled(self):
        started = asyncio.Event()

        async def full_runner(context, parameters):
            await context.set_stage(TaskStage.LISTING, message="listing", progress_current=1, progress_total=10, progress_unit="page")
            started.set()
            while True:
                await asyncio.sleep(0.01)
                await context.check_cancelled()

        self.service = TaskService(source="dongchedi", runners={TaskType.FULL: full_runner})
        await self.service.startup()

        task = self.service.create_task(TaskCreateRequest(task_type=TaskType.FULL))
        await asyncio.wait_for(started.wait(), timeout=2)

        cancelled = self.service.cancel_task(task.id)
        self.assertTrue(cancelled.cancel_requested)

        await asyncio.wait_for(self.service._queue.join(), timeout=2)

        snapshot = self.service.get_task(task.id)
        self.assertEqual(snapshot.status, TaskStatus.CANCELLED)
        self.assertEqual(snapshot.stage, TaskStage.CANCELLED)
        self.assertFalse(snapshot.result_available)

    async def test_task_failure_preserves_error_message(self):
        async def detailed_runner(context, parameters):
            await context.set_stage(TaskStage.DETAILED, message="detailed", progress_current=0, progress_total=1, progress_unit="car")
            raise RuntimeError("boom")

        self.service = TaskService(source="che168", runners={TaskType.DETAILED: detailed_runner})
        await self.service.startup()

        task = self.service.create_task(TaskCreateRequest(task_type=TaskType.DETAILED))
        await asyncio.wait_for(self.service._queue.join(), timeout=2)

        snapshot = self.service.get_task(task.id)
        self.assertEqual(snapshot.status, TaskStatus.FAILED)
        self.assertEqual(snapshot.stage, TaskStage.FAILED)
        self.assertEqual(snapshot.error_message, "boom")

    def test_normalize_detailed_items_for_dongchedi(self):
        items = _normalize_detailed_items(
            "dongchedi",
            {
                "items": [
                    {"external_id": "39813", "secondary_id": "dc-car-1", "force_update": True},
                    {"external_id": 39814},
                ]
            },
        )

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["external_id"], "39813")
        self.assertEqual(items[0]["secondary_id"], "dc-car-1")
        self.assertTrue(items[0]["force_update"])
        self.assertEqual(items[1]["external_id"], "39814")
        self.assertIsNone(items[1]["secondary_id"])

    def test_normalize_detailed_items_for_che168_requires_secondary_id(self):
        with self.assertRaisesRegex(ValueError, "secondary_id"):
            _normalize_detailed_items(
                "che168",
                {"items": [{"external_id": "57885738"}]},
            )

        items = _normalize_detailed_items(
            "che168",
            {"items": [{"external_id": "57885738", "secondary_id": "629891", "force_update": False}]},
        )
        self.assertEqual(items[0]["external_id"], "57885738")
        self.assertEqual(items[0]["secondary_id"], "629891")
        self.assertFalse(items[0]["force_update"])

    def test_normalize_detailed_items_rejects_legacy_parameter_shapes(self):
        with self.assertRaisesRegex(ValueError, "parameters.items"):
            _normalize_detailed_items("dongchedi", {"car_ids": ["39813"]})

        with self.assertRaisesRegex(ValueError, "parameters.items"):
            _normalize_detailed_items(
                "che168",
                {"requests": [{"car_id": 57885738, "shop_id": 629891}]},
            )

    def test_batch_delivery_state_requires_endpoint_for_push_mode(self):
        with mock.patch.dict("os.environ", {"DATAHUB_URL": "", "DATAHUB_BATCH_ENDPOINT": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "batch_endpoint"):
                _build_batch_delivery_state({"delivery_mode": "push_batches"})

        state = _build_batch_delivery_state(
            {
                "delivery_mode": "push_batches",
                "batch_endpoint": "http://datahub/parser/batches",
                "batch_size": 2,
            }
        )

        self.assertEqual(state.endpoint, "http://datahub/parser/batches")
        self.assertEqual(state.batch_size, 2)
        self.assertEqual(_delivery_summary(state)["delivery_mode"], "push_batches")

    def test_append_unique_listing_deduplicates_within_task(self):
        seen = set()
        self.assertTrue(_append_unique_listing(seen, "encar", {"car_id": 1, "sku_id": "1"}))
        self.assertFalse(_append_unique_listing(seen, "encar", {"car_id": 1, "sku_id": "1"}))
        self.assertTrue(_append_unique_listing(seen, "encar", {"car_id": 2, "sku_id": "2"}))
        self.assertEqual(len(seen), 2)

    def test_post_parser_batch_sends_idempotency_headers(self):
        fake_response = mock.Mock()
        fake_response.content = b'{"status":202}'
        fake_response.json.return_value = {"status": 202}
        fake_response.raise_for_status.return_value = None

        payload = {
            "task_id": "task-1",
            "batch_id": "task-1:1",
            "items": [{"car_id": 1}],
        }

        with mock.patch("task_service.requests.post", return_value=fake_response) as mocked_post:
            result = _post_parser_batch(
                endpoint="http://datahub/parser/batches",
                payload=payload,
                timeout_seconds=10,
                auth_token="secret",
            )

        self.assertEqual(result, {"status": 202})
        kwargs = mocked_post.call_args.kwargs
        self.assertEqual(kwargs["json"], payload)
        self.assertEqual(kwargs["headers"]["Idempotency-Key"], "task-1:1")
        self.assertEqual(kwargs["headers"]["X-Parser-Task-Id"], "task-1")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")

    async def test_final_batch_marker_is_sent_when_buffer_is_empty(self):
        class Context:
            task_id = "task-1"

            async def run_sync(self, func, *args, **kwargs):
                return func(*args, **kwargs)

            async def update(self, **kwargs):
                self.last_update = kwargs

        delivery = BatchDeliveryState(
            endpoint="http://datahub/parser/batches",
            batch_size=2,
            timeout_seconds=10,
            max_retries=1,
        )

        with mock.patch("task_service.requests.post") as mocked_post:
            fake_response = mock.Mock()
            fake_response.content = b""
            fake_response.raise_for_status.return_value = None
            mocked_post.return_value = fake_response

            await _flush_listing_batch(
                Context(),
                delivery,
                source="encar",
                task_type=TaskType.FULL,
                page=2,
                final=True,
            )

        payload = mocked_post.call_args.kwargs["json"]
        self.assertEqual(payload["batch_id"], "task-1:1")
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["item_count"], 0)
        self.assertTrue(payload["is_final"])

    async def test_push_batches_runs_for_all_sources_and_listing_task_types(self):
        parser_patches = {
            "dongchedi": "api.dongchedi.parser.DongchediParser.fetch_cars_by_page",
            "che168": "api.che168.parser.Che168Parser.fetch_cars_by_page",
            "encar": "api.encar.parser.EncarParser.fetch_cars_by_page",
        }

        for source, patch_target in parser_patches.items():
            for task_type in (TaskType.FULL, TaskType.INCREMENTAL):
                with self.subTest(source=source, task_type=task_type.value):
                    payloads = []

                    def fake_post(endpoint, *, json, headers, timeout):
                        payloads.append(json)
                        response = mock.Mock()
                        response.content = b'{"status":202}'
                        response.json.return_value = {"status": 202}
                        response.raise_for_status.return_value = None
                        return response

                    with mock.patch(patch_target, side_effect=self._fake_listing_response), mock.patch("task_service.requests.post", side_effect=fake_post):
                        service = build_task_service(source)
                        await service.startup()
                        try:
                            task = service.create_task(
                                TaskCreateRequest(
                                    task_type=task_type,
                                    parameters={
                                        "delivery_mode": "push_batches",
                                        "batch_endpoint": "http://datahub/parser/batches",
                                        "batch_size": 2,
                                    },
                                )
                            )
                            await asyncio.wait_for(service._queue.join(), timeout=10)

                            snapshot = service.get_task(task.id)
                            self.assertEqual(snapshot.status, TaskStatus.SUCCEEDED)
                            self.assertEqual(snapshot.stage, TaskStage.COMPLETED)
                            self.assertEqual(snapshot.items_found, 3)
                            self.assertEqual(snapshot.items_sent, 3)
                            self.assertEqual(snapshot.result_summary["delivery_mode"], "push_batches")
                            self.assertEqual(snapshot.result_summary["batches_sent"], 2)
                            self.assertEqual(snapshot.result_summary["items_sent"], 3)

                            result = service.get_task_result(task.id)
                            self.assertEqual(result.result, [])
                        finally:
                            await service.shutdown()

                    self.assertEqual([payload["source"] for payload in payloads], [source, source])
                    self.assertEqual([payload["task_type"] for payload in payloads], [task_type.value, task_type.value])
                    self.assertEqual([payload["item_count"] for payload in payloads], [2, 1])
                    self.assertEqual([payload["is_final"] for payload in payloads], [False, True])
                    delivered_ids = [item["car_id"] for payload in payloads for item in payload["items"]]
                    self.assertEqual(delivered_ids, [101, 102, 103])

    @staticmethod
    def _fake_listing_response(page):
        pages = {
            1: ([101, 102], True),
            2: ([102, 103], False),
        }
        ids, has_more = pages.get(page, ([], False))
        cars = [FakeListingCar(car_id) for car_id in ids]
        return SimpleNamespace(
            data=SimpleNamespace(
                search_sh_sku_info_list=cars,
                has_more=has_more,
            )
        )


class FakeListingCar:
    def __init__(self, car_id):
        self.car_id = car_id

    def dict(self, *args, **kwargs):
        return {
            "car_id": self.car_id,
            "sku_id": str(self.car_id),
            "shop_id": self.car_id + 1000,
            "title": f"Fake car {self.car_id} 2022",
            "year": 2022,
            "car_year": 2022,
            "image": f"https://example.test/{self.car_id}.jpg",
            "link": f"https://example.test/cars/{self.car_id}",
        }


if __name__ == "__main__":
    unittest.main()
