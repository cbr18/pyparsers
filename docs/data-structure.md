# Структура данных и контракт задач

## Что хранит `pyparsers`

`pyparsers` больше не являются системой истины для бизнес-статусов в `datahub`.
Они хранят только runtime-состояние исполнения parser job:

- текущий lifecycle задачи;
- heartbeat;
- progress;
- summary/result до истечения TTL.

Оркестрация, финальные решения и долговременное хранение остаются на стороне `datahub`.

## Lifecycle задачи в `pyparsers`

Поддерживаемые статусы:

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

Поддерживаемые стадии:

- `queued`
- `initializing`
- `listing`
- `detailed`
- `finalizing`
- `completed`
- `failed`
- `cancelled`

Поддерживаемые типы задач:

- `full`
- `incremental`
- `detailed`

## Унифицированный snapshot задачи

`GET /tasks/{task_id}` возвращает snapshot такого вида:

```json
{
  "id": "0f34f8c3-2e2f-4b2c-bf78-4f95d9c37012",
  "source": "dongchedi",
  "task_type": "incremental",
  "status": "running",
  "stage": "listing",
  "message": "Parsed dongchedi page 3",
  "error_message": null,
  "parameters": {
    "id_field": "sku_id",
    "existing_ids": [
      "1234567890"
    ]
  },
  "metadata": {
    "requested_by": "datahub"
  },
  "progress_current": 3,
  "progress_total": 100,
  "progress_unit": "page",
  "items_found": 148,
  "items_processed": 0,
  "items_sent": 0,
  "cancel_requested": false,
  "result_available": false,
  "result_summary": {},
  "created_at": "2026-04-07T01:10:12.884661Z",
  "started_at": "2026-04-07T01:10:12.885470Z",
  "finished_at": null,
  "updated_at": "2026-04-07T01:10:18.102202Z",
  "heartbeat_at": "2026-04-07T01:10:18.102202Z",
  "result_fetched_at": null
}
```

## Создание задачи

`POST /tasks`

```json
{
  "task_type": "incremental",
  "parameters": {
    "id_field": "sku_id",
    "existing_ids": [
      "1234567890"
    ]
  },
  "metadata": {
    "requested_by": "datahub"
  }
}
```

Поддерживаемые параметры:

### `dongchedi`

- `full`
  - специальных параметров не требует
- `incremental`
  - `existing_ids: string[]`
  - `id_field: "sku_id" | "car_id"`; по умолчанию `sku_id`
- `detailed`
  - `items: [{ "external_id": string, "secondary_id"?: string, "force_update"?: boolean }]`

### `che168`

- `full`
  - специальных параметров не требует
- `incremental`
  - `existing_ids: string[]`
  - `id_field: string`; по умолчанию `car_id`
- `detailed`
  - `items: [{ "external_id": string, "secondary_id": string, "force_update"?: boolean }]`

## Получение результата

После `status=succeeded` результат забирается отдельно через `GET /tasks/{task_id}/result`.

Ответ:

```json
{
  "task": {
    "id": "0f34f8c3-2e2f-4b2c-bf78-4f95d9c37012",
    "source": "dongchedi",
    "task_type": "incremental",
    "status": "succeeded",
    "stage": "completed",
    "result_available": true
  },
  "result": [
    {
      "car_id": 39813,
      "sku_id": "6982515711322382375",
      "title": "Porsche 718 2020",
      "source": "dongchedi"
    }
  ]
}
```

Результат хранится ограниченное время:

- snapshot задачи живёт `TASK_TTL_HOURS`;
- payload результата живёт `TASK_RESULT_TTL_MINUTES`.

После истечения TTL snapshot может остаться, но `result_available` станет `false`.

## Отмена задачи

`POST /tasks/{task_id}/cancel`

Поведение:

- если задача ещё не стартовала, она переходит в `cancelled` сразу;
- если задача уже выполняется, ставится `cancel_requested=true`, а runner завершает её кооперативно.

## Progress semantics

Во всех типах задач используются одни и те же поля:

- `progress_current`
- `progress_total`
- `progress_unit`
- `items_found`
- `items_processed`
- `items_sent`
- `heartbeat_at`

Типичные значения:

- `full`
  - `progress_unit=page`
- `incremental`
  - `progress_unit=page`
- `detailed`
  - `progress_unit=car`

`progress_total` может быть оценочным, особенно для listing-задач.

## Базовые поля машин

Ниже перечислены только основные поля, которые чаще всего использует `datahub`.
Детальные payload'ы зависят от источника и режима парсинга.

### CHE168

```json
{
  "car_id": 57885738,
  "shop_id": 629891,
  "title": "2020 Mercedes-Benz C200",
  "price": 25.8,
  "image": "https://image.che168.com/example.jpg",
  "link": "https://m.che168.com/cardetail/index?infoid=57885738",
  "brand_name": "Mercedes-Benz",
  "series_name": "C-Class",
  "year": 2020,
  "mileage": 52000,
  "city": "Shanghai",
  "source": "che168",
  "sort_number": 56
}
```

### DONGCHEDI

```json
{
  "car_id": 39813,
  "sku_id": "6982515711322382375",
  "title": "Porsche 718 2020",
  "price": 39.98,
  "image": "https://image.dongchedi.com/example.jpg",
  "link": "https://www.dongchedi.com/usedcar/39813",
  "brand_name": "Porsche",
  "series_name": "718",
  "year": 2020,
  "mileage": 41000,
  "city": "Shanghai",
  "source": "dongchedi",
  "sort_number": 62
}
```
