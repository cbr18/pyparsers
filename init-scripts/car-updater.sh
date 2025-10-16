#!/bin/bash

set -o pipefail

# Логи сохраняем в примонтированную директорию контейнера
LOG_FILE="/logs/car-updater.log"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  echo "[$(timestamp)] $1" >> "$LOG_FILE"
}

# Базовый URL для datahub — берем из переменной окружения или используем адрес сервиса в докер-сети
DATAHUB_URL_DEFAULT="http://datahub:8080"
BASE_URL="${DATAHUB_URL:-$DATAHUB_URL_DEFAULT}"

make_get() {
  url="$1"
  log "GET $url"
  # -L следовать редиректам, -f fail on HTTP errors, -S показать ошибку, --max-time ограничение
  if curl -s -L -f -S -X GET --max-time 3600 "$url" >/dev/null; then
    log "GET $url finished"
  else
    rc=$?
    log "GET $url failed (rc=$rc)"
  fi
}

make_post() {
  url="$1"
  data="$2"
  log "POST $url"
  if curl -s -L -f -S -X POST -H "Content-Type: application/json" -d "$data" --max-time 3600 "$url" >/dev/null; then
    log "POST $url finished"
  else
    rc=$?
    log "POST $url failed (rc=$rc)"
  fi
}

# Параметр $1 — тип запуска: dongchedi, che168, dongchedi-full, che168-full
case "$1" in
  dongchedi)
    make_post "${BASE_URL}/api/update/dongchedi" '{"last_n":10}'
    ;;
  che168)
    make_post "${BASE_URL}/api/update/che168" '{"last_n":10}'
    ;;
  dongchedi-full)
    make_get  "${BASE_URL}/api/update/dongchedi/full"
    ;;
  che168-full)
    make_get  "${BASE_URL}/api/update/che168/full"
    ;;
  *)
    log "Unknown parameter: $1"
    exit 1
    ;;
esac