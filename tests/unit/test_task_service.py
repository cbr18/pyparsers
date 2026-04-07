import asyncio
import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pyparsers"))

from models import TaskCreateRequest, TaskStage, TaskStatus, TaskType
from task_service import TaskRunResult, TaskService, _normalize_detailed_items


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


if __name__ == "__main__":
    unittest.main()
