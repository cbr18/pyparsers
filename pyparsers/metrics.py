from __future__ import annotations

import math
import threading
import time
from collections import defaultdict
from collections.abc import Iterable
from typing import Any


LabelTuple = tuple[tuple[str, str], ...]


def _label_key(labels: dict[str, Any]) -> LabelTuple:
    return tuple(sorted((name, str(value)) for name, value in labels.items()))


def _format_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_labels(labels: LabelTuple) -> str:
    if not labels:
        return ""
    rendered = ",".join(f'{name}="{_format_label_value(value)}"' for name, value in labels)
    return f"{{{rendered}}}"


class CounterMetric:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._values: dict[LabelTuple, float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0, **labels: Any) -> None:
        if amount < 0:
            return
        key = _label_key(labels)
        with self._lock:
            self._values[key] += amount

    def collect(self) -> list[str]:
        with self._lock:
            values = list(self._values.items())
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        for labels, value in values:
            lines.append(f"{self.name}{_format_labels(labels)} {value:g}")
        return lines


class GaugeMetric:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._values: dict[LabelTuple, float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, **labels: Any) -> None:
        key = _label_key(labels)
        with self._lock:
            self._values[key] = value

    def inc(self, amount: float = 1.0, **labels: Any) -> None:
        key = _label_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, amount: float = 1.0, **labels: Any) -> None:
        self.inc(-amount, **labels)

    def reset_where(self, **match_labels: Any) -> None:
        match = {name: str(value) for name, value in match_labels.items()}
        with self._lock:
            for labels in list(self._values):
                label_dict = dict(labels)
                if all(label_dict.get(name) == value for name, value in match.items()):
                    self._values[labels] = 0.0

    def collect(self) -> list[str]:
        with self._lock:
            values = list(self._values.items())
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        for labels, value in values:
            lines.append(f"{self.name}{_format_labels(labels)} {value:g}")
        return lines


class HistogramMetric:
    def __init__(self, name: str, description: str, buckets: Iterable[float]):
        self.name = name
        self.description = description
        self.buckets = tuple(sorted(float(bucket) for bucket in buckets))
        self._bucket_values: dict[LabelTuple, list[int]] = {}
        self._sums: dict[LabelTuple, float] = defaultdict(float)
        self._counts: dict[LabelTuple, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, **labels: Any) -> None:
        if value < 0 or math.isnan(value):
            return
        key = _label_key(labels)
        with self._lock:
            counts = self._bucket_values.setdefault(key, [0] * len(self.buckets))
            for index, bucket in enumerate(self.buckets):
                if value <= bucket:
                    counts[index] += 1
            self._sums[key] += value
            self._counts[key] += 1

    def collect(self) -> list[str]:
        with self._lock:
            bucket_values = {labels: list(values) for labels, values in self._bucket_values.items()}
            sums = dict(self._sums)
            counts = dict(self._counts)
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        for labels, values in bucket_values.items():
            label_dict = dict(labels)
            for bucket, count in zip(self.buckets, values):
                bucket_labels = _label_key({**label_dict, "le": f"{bucket:g}"})
                lines.append(f"{self.name}_bucket{_format_labels(bucket_labels)} {count}")
            inf_labels = _label_key({**label_dict, "le": "+Inf"})
            lines.append(f"{self.name}_bucket{_format_labels(inf_labels)} {counts.get(labels, 0)}")
            lines.append(f"{self.name}_sum{_format_labels(labels)} {sums.get(labels, 0.0):g}")
            lines.append(f"{self.name}_count{_format_labels(labels)} {counts.get(labels, 0)}")
        return lines


REQUESTS_TOTAL = CounterMetric("pyparsers_http_requests_total", "Total HTTP requests handled by parser services.")
REQUEST_DURATION = HistogramMetric(
    "pyparsers_http_request_duration_seconds",
    "HTTP request duration by parser service and normalized route.",
    (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)
REQUESTS_IN_PROGRESS = GaugeMetric("pyparsers_http_requests_in_progress", "HTTP requests currently in progress.")

TASKS_CREATED = CounterMetric("pyparsers_tasks_created_total", "Parser tasks created.")
TASKS_COMPLETED = CounterMetric("pyparsers_tasks_completed_total", "Parser tasks completed by terminal status.")
TASK_DURATION = HistogramMetric(
    "pyparsers_task_duration_seconds",
    "Parser task execution duration.",
    (1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600, 7200),
)
TASKS_ACTIVE = GaugeMetric("pyparsers_tasks_active", "Current parser tasks by task type, status, and stage.")
TASK_QUEUE_SIZE = GaugeMetric("pyparsers_task_queue_size", "Current parser task queue size.")
TASK_RECORDS = GaugeMetric("pyparsers_task_records", "Current task records retained in memory.")
TASK_RESULTS_CACHED = GaugeMetric("pyparsers_results_cached", "Current task results retained in memory.")
TASK_ITEMS_FOUND = CounterMetric("pyparsers_task_items_found_total", "Items found by completed parser tasks.")
TASK_ITEMS_SENT = CounterMetric("pyparsers_task_items_sent_total", "Items sent or returned by completed parser tasks.")

LISTING_PAGES_SCANNED = CounterMetric("pyparsers_listing_pages_scanned_total", "Listing pages scanned by parser tasks.")
LISTING_ITEMS_FOUND = CounterMetric("pyparsers_listing_items_found_total", "Listing items found by parser tasks.")
LISTING_ITEMS_FILTERED = CounterMetric("pyparsers_listing_items_filtered_total", "Listing items filtered by stable reason.")
LISTING_EMPTY_PAGES = CounterMetric("pyparsers_listing_empty_pages_total", "Listing pages that returned no cars.")

BATCH_ATTEMPTS = CounterMetric("pyparsers_batch_delivery_attempts_total", "DataHub batch delivery attempts.")
BATCH_DURATION = HistogramMetric(
    "pyparsers_batch_delivery_duration_seconds",
    "DataHub batch delivery attempt duration.",
    (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)
BATCH_ITEMS_SENT = CounterMetric("pyparsers_batch_items_sent_total", "Items accepted by DataHub batch delivery.")
BATCH_SIZE_ITEMS = HistogramMetric(
    "pyparsers_batch_size_items",
    "DataHub parser batch size in items.",
    (0, 1, 5, 10, 25, 50, 100, 250, 500, 1000),
)
BATCH_RETRIES = CounterMetric("pyparsers_batch_retries_total", "DataHub batch delivery retry attempts.")
BATCH_FAILURES = CounterMetric("pyparsers_batch_failures_total", "DataHub parser batches that failed after all retries.")
BATCH_FINAL = CounterMetric("pyparsers_batch_final_total", "Final parser batches sent to DataHub.")

SOURCE_PROBES = CounterMetric("pyparsers_source_probe_total", "Source availability probe results.")
SOURCE_PROBE_DURATION = HistogramMetric(
    "pyparsers_source_probe_duration_seconds",
    "Source availability probe duration.",
    (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)
SOURCE_BLOCKED = GaugeMetric("pyparsers_source_blocked", "Source blocked status from the last probe, 1 means blocked.")

CHE168_DETAIL_REQUESTS = CounterMetric("pyparsers_che168_detail_requests_total", "che168 detail endpoint requests.")
CHE168_DETAIL_DURATION = HistogramMetric(
    "pyparsers_che168_detail_duration_seconds",
    "che168 detail endpoint request duration.",
    (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)
CHE168_DETAIL_BATCH_SIZE = HistogramMetric(
    "pyparsers_che168_detail_batch_size_items",
    "che168 detail batch request size.",
    (0, 1, 2, 5, 10, 25, 50, 100),
)
CHE168_DETAIL_BATCH_ITEMS = CounterMetric("pyparsers_che168_detail_batch_items_total", "che168 detail batch item results.")
CHE168_DETAIL_INFLIGHT = GaugeMetric("pyparsers_che168_detail_inflight", "che168 detail parses currently owned by this process.")
CHE168_DETAIL_COALESCED = CounterMetric("pyparsers_che168_detail_coalesced_total", "che168 detail requests coalesced onto in-flight work.")
CHE168_DETAIL_FAILURE_CACHE_HITS = CounterMetric("pyparsers_che168_detail_failure_cache_hits_total", "che168 detail failure-cache hits.")
CHE168_DETAIL_FAILURE_CACHE_WRITES = CounterMetric("pyparsers_che168_detail_failure_cache_writes_total", "che168 detail failure-cache writes.")
CHE168_FALLBACK_ATTEMPTS = CounterMetric("pyparsers_che168_fallback_attempts_total", "che168 Selenium/mobile fallback attempts.")
CHE168_FALLBACK_DURATION = HistogramMetric(
    "pyparsers_che168_fallback_duration_seconds",
    "che168 Selenium/mobile fallback duration.",
    (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)
CHE168_FALLBACK_IN_PROGRESS = GaugeMetric("pyparsers_che168_fallback_in_progress", "che168 fallback operations currently in progress.")

BUILD_INFO = GaugeMetric("pyparsers_build_info", "Parser service build and source information.")

_METRICS = (
    REQUESTS_TOTAL,
    REQUEST_DURATION,
    REQUESTS_IN_PROGRESS,
    TASKS_CREATED,
    TASKS_COMPLETED,
    TASK_DURATION,
    TASKS_ACTIVE,
    TASK_QUEUE_SIZE,
    TASK_RECORDS,
    TASK_RESULTS_CACHED,
    TASK_ITEMS_FOUND,
    TASK_ITEMS_SENT,
    LISTING_PAGES_SCANNED,
    LISTING_ITEMS_FOUND,
    LISTING_ITEMS_FILTERED,
    LISTING_EMPTY_PAGES,
    BATCH_ATTEMPTS,
    BATCH_DURATION,
    BATCH_ITEMS_SENT,
    BATCH_SIZE_ITEMS,
    BATCH_RETRIES,
    BATCH_FAILURES,
    BATCH_FINAL,
    SOURCE_PROBES,
    SOURCE_PROBE_DURATION,
    SOURCE_BLOCKED,
    CHE168_DETAIL_REQUESTS,
    CHE168_DETAIL_DURATION,
    CHE168_DETAIL_BATCH_SIZE,
    CHE168_DETAIL_BATCH_ITEMS,
    CHE168_DETAIL_INFLIGHT,
    CHE168_DETAIL_COALESCED,
    CHE168_DETAIL_FAILURE_CACHE_HITS,
    CHE168_DETAIL_FAILURE_CACHE_WRITES,
    CHE168_FALLBACK_ATTEMPTS,
    CHE168_FALLBACK_DURATION,
    CHE168_FALLBACK_IN_PROGRESS,
    BUILD_INFO,
)


def normalized_route(request: Any) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return str(route_path)
    return request.url.path


def source_from_request(request: Any) -> str:
    return str(getattr(request.app.state, "source", "legacy"))


def observe_http_request(
    *,
    source: str,
    method: str,
    path: str,
    status: int,
    duration_seconds: float,
) -> None:
    labels = {"source": source, "method": method, "path": path, "status": str(status)}
    REQUESTS_TOTAL.inc(**labels)
    REQUEST_DURATION.observe(duration_seconds, **labels)


def refresh_task_inventory(source: str, tasks: Iterable[Any], results_cached: int, queue_size: int) -> None:
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    total_by_status: dict[str, int] = defaultdict(int)
    for task in tasks:
        task_type = getattr(getattr(task, "task_type", ""), "value", getattr(task, "task_type", "unknown"))
        status = getattr(getattr(task, "status", ""), "value", getattr(task, "status", "unknown"))
        stage = getattr(getattr(task, "stage", ""), "value", getattr(task, "stage", "unknown"))
        counts[(str(task_type), str(status), str(stage))] += 1
        total_by_status[str(status)] += 1

    TASKS_ACTIVE.reset_where(source=source)
    TASK_RECORDS.reset_where(source=source)

    for task_type, status, stage in counts:
        TASKS_ACTIVE.set(counts[(task_type, status, stage)], source=source, task_type=task_type, status=status, stage=stage)

    for status, count in total_by_status.items():
        TASK_RECORDS.set(count, source=source, status=status)
    TASK_QUEUE_SIZE.set(queue_size, source=source)
    TASK_RESULTS_CACHED.set(results_cached, source=source)


def observe_task_created(source: str, task_type: str) -> None:
    TASKS_CREATED.inc(source=source, task_type=task_type)


def observe_task_completed(
    *,
    source: str,
    task_type: str,
    status: str,
    duration_seconds: float | None,
    items_found: int,
    items_sent: int,
) -> None:
    TASKS_COMPLETED.inc(source=source, task_type=task_type, status=status)
    if duration_seconds is not None:
        TASK_DURATION.observe(duration_seconds, source=source, task_type=task_type, status=status)
    if items_found:
        TASK_ITEMS_FOUND.inc(items_found, source=source, task_type=task_type)
    if items_sent:
        TASK_ITEMS_SENT.inc(items_sent, source=source, task_type=task_type)


def observe_listing_summary(source: str, task_type: str, pages_scanned: int, items_found: int) -> None:
    if pages_scanned:
        LISTING_PAGES_SCANNED.inc(pages_scanned, source=source, task_type=task_type)
    if items_found:
        LISTING_ITEMS_FOUND.inc(items_found, source=source, task_type=task_type)


def render_metrics() -> str:
    now = int(time.time())
    lines = [
        "# HELP pyparsers_metrics_scrape_timestamp_seconds Unix timestamp when metrics were rendered.",
        "# TYPE pyparsers_metrics_scrape_timestamp_seconds gauge",
        f"pyparsers_metrics_scrape_timestamp_seconds {now}",
    ]
    for metric in _METRICS:
        lines.extend(metric.collect())
    return "\n".join(lines) + "\n"


async def metrics_response() -> Response:
    from fastapi import Response

    return Response(render_metrics(), media_type="text/plain; version=0.0.4; charset=utf-8")
