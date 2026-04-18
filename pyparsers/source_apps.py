from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import async_api_server
from models import TaskCreateRequest
from task_service import build_task_service


def _build_root_handler(source: str, endpoints: dict[str, str]) -> Callable[[], dict]:
    async def root():
        return {
            "data": {
                "name": f"Async Car Parsers API ({source})",
                "version": "1.0.0",
                "source": source,
                "description": f"Direct API for the {source} parser service",
                "endpoints": endpoints,
            },
            "message": "Welcome to Async Car Parsers API",
            "status": 200,
        }

    return root


def _build_base_app(source: str, endpoints: dict[str, str]) -> FastAPI:
    app = FastAPI(
        title=f"Async Car Parsers API ({source})",
        description=f"Direct API for the {source} parser service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        async_api_server.IPWhitelistMiddleware,
        public_paths={"/", "/health", "/blocked"},
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=async_api_server.cors_origins,
        allow_credentials=async_api_server.cors_credentials,
        allow_methods=async_api_server.cors_methods,
        allow_headers=async_api_server.cors_headers,
    )
    task_service = build_task_service(source)
    app.state.task_service = task_service
    app.middleware("http")(async_api_server.add_performance_info)
    app.add_event_handler("startup", task_service.startup)
    app.add_event_handler("shutdown", async_api_server.shutdown_event)
    app.add_event_handler("shutdown", task_service.shutdown)
    app.add_api_route("/", _build_root_handler(source, endpoints), methods=["GET"])
    app.add_api_route("/health", async_api_server.health_check, methods=["GET", "HEAD"])
    app.add_api_route("/tasks", _create_task(task_service), methods=["POST"])
    app.add_api_route("/tasks", _list_tasks(task_service), methods=["GET"])
    app.add_api_route("/tasks/{task_id}", _get_task(task_service), methods=["GET"])
    app.add_api_route("/tasks/{task_id}/result", _get_task_result(task_service), methods=["GET"])
    app.add_api_route("/tasks/{task_id}/cancel", _cancel_task(task_service), methods=["POST"])
    return app


def _create_task(task_service):
    async def handler(request: TaskCreateRequest):
        try:
            task = task_service.create_task(request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "data": task.model_dump(mode="json"),
            "message": "Task created",
            "status": 202,
        }

    return handler


def _list_tasks(task_service):
    async def handler():
        tasks = [task.model_dump(mode="json") for task in task_service.list_tasks()]
        return {
            "data": {
                "items": tasks,
                "total": len(tasks),
            },
            "message": "Tasks fetched",
            "status": 200,
        }

    return handler


def _get_task(task_service):
    async def handler(task_id: str):
        task = task_service.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "data": task.model_dump(mode="json"),
            "message": "Task fetched",
            "status": 200,
        }

    return handler


def _get_task_result(task_service):
    async def handler(task_id: str):
        envelope = task_service.get_task_result(task_id)
        if envelope is None:
            raise HTTPException(status_code=404, detail="Task result not found")
        return {
            "data": envelope.model_dump(mode="json"),
            "message": "Task result fetched",
            "status": 200,
        }

    return handler


def _cancel_task(task_service):
    async def handler(task_id: str):
        task = task_service.cancel_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "data": task.model_dump(mode="json"),
            "message": "Task cancellation requested",
            "status": 200,
        }

    return handler


def _build_dongchedi_app() -> FastAPI:
    endpoints = {
        "blocked": "/blocked",
        "cars": "/cars",
        "cars_page": "/cars/page/{page}",
        "cars_all": "/cars/all",
        "cars_incremental": "/cars/incremental",
        "cars_detail": "/cars/car/{sku_id}",
        "cars_batch_detail": "/cars/cars",
        "cars_stats": "/cars/stats",
        "cars_enhance": "/cars/enhance/{sku_id}",
        "cars_specs": "/cars/specs/{car_id}",
        "cars_batch_enhance": "/cars/batch-enhance",
        "update_full": "/update/full",
        "tasks": "/tasks",
        "task": "/tasks/{task_id}",
        "task_result": "/tasks/{task_id}/result",
        "task_cancel": "/tasks/{task_id}/cancel",
        "docs": "/docs",
        "redoc": "/redoc",
    }
    app = _build_base_app("dongchedi", endpoints)
    app.add_api_route("/blocked", async_api_server.get_dongchedi_blocked_status, methods=["GET"])
    app.add_api_route("/cars", async_api_server.get_dongchedi_cars, methods=["GET"])
    app.add_api_route("/cars/page/{page}", async_api_server.get_dongchedi_cars_by_page, methods=["GET"])
    app.add_api_route("/cars/all", async_api_server.get_dongchedi_all_cars, methods=["GET"])
    app.add_api_route("/cars/incremental", async_api_server.get_dongchedi_incremental_cars, methods=["POST"])
    app.add_api_route("/cars/car/{sku_id}", async_api_server.get_dongchedi_car_detail, methods=["GET"])
    app.add_api_route("/cars/cars", async_api_server.get_dongchedi_multiple_cars, methods=["POST"])
    app.add_api_route("/cars/stats", async_api_server.get_dongchedi_stats, methods=["GET"])
    app.add_api_route("/cars/enhance/{sku_id}", async_api_server.enhance_dongchedi_car, methods=["GET"])
    app.add_api_route("/cars/specs/{car_id}", async_api_server.get_dongchedi_car_specs, methods=["GET"])
    app.add_api_route("/cars/batch-enhance", async_api_server.batch_enhance_dongchedi_cars, methods=["POST"])
    app.add_api_route("/update/full", async_api_server.update_dongchedi_full, methods=["GET"])
    return app


def _build_che168_app() -> FastAPI:
    endpoints = {
        "blocked": "/blocked",
        "cars": "/cars",
        "cars_page": "/cars/page/{page}",
        "cars_all": "/cars/all",
        "cars_incremental": "/cars/incremental",
        "cars_detail": "/cars/car",
        "detailed_parse": "/detailed/parse",
        "detailed_parse_batch": "/detailed/parse-batch",
        "detailed_health": "/detailed/health",
        "update_full": "/update/full",
        "tasks": "/tasks",
        "task": "/tasks/{task_id}",
        "task_result": "/tasks/{task_id}/result",
        "task_cancel": "/tasks/{task_id}/cancel",
        "docs": "/docs",
        "redoc": "/redoc",
    }
    app = _build_base_app("che168", endpoints)
    app.include_router(async_api_server.che168_detailed_router)
    app.add_api_route("/blocked", async_api_server.get_che168_blocked_status, methods=["GET"])
    app.add_api_route("/cars", async_api_server.get_che168_cars, methods=["GET"])
    app.add_api_route("/cars/page/{page}", async_api_server.get_che168_cars_by_page, methods=["GET"])
    app.add_api_route("/cars/all", async_api_server.get_che168_all_cars, methods=["GET"])
    app.add_api_route("/cars/incremental", async_api_server.get_che168_incremental_cars, methods=["POST"])
    app.add_api_route("/cars/car", async_api_server.get_che168_car_detail, methods=["POST"])
    app.add_api_route("/update/full", async_api_server.update_che168_full, methods=["GET"])
    return app


def _build_encar_app() -> FastAPI:
    endpoints = {
        "blocked": "/blocked",
        "cars": "/cars",
        "cars_page": "/cars/page/{page}",
        "cars_all": "/cars/all",
        "cars_incremental": "/cars/incremental",
        "cars_detail": "/cars/car/{car_id}",
        "update_full": "/update/full",
        "tasks": "/tasks",
        "task": "/tasks/{task_id}",
        "task_result": "/tasks/{task_id}/result",
        "task_cancel": "/tasks/{task_id}/cancel",
        "docs": "/docs",
        "redoc": "/redoc",
    }
    app = _build_base_app("encar", endpoints)
    app.add_api_route("/blocked", async_api_server.get_encar_blocked_status, methods=["GET"])
    app.add_api_route("/cars", async_api_server.get_encar_cars, methods=["GET"])
    app.add_api_route("/cars/page/{page}", async_api_server.get_encar_cars_by_page, methods=["GET"])
    app.add_api_route("/cars/all", async_api_server.get_encar_all_cars, methods=["GET"])
    app.add_api_route("/cars/incremental", async_api_server.get_encar_incremental_cars, methods=["POST"])
    app.add_api_route("/cars/car/{car_id}", async_api_server.get_encar_car_detail, methods=["GET"])
    app.add_api_route("/update/full", async_api_server.update_encar_full, methods=["GET"])
    return app


def build_source_app(source: str):
    if source == "dongchedi":
        return _build_dongchedi_app()
    if source == "che168":
        return _build_che168_app()
    if source == "encar":
        return _build_encar_app()
    raise ValueError(f"Unsupported source: {source}")
