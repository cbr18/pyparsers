#!/bin/bash

log_file="/var/log/car-updater.log"
timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

log() {
  echo "[$timestamp] $1" >> "$log_file"
}

make_get() {
  url="$1"
  log "GET $url"
  curl -s -X GET --max-time 3600 "$url" >/dev/null 2>&1
  log "GET $url finished"
}

make_post() {
  url="$1"
  data="$2"
  log "POST $url"
  curl -s -X POST -H "Content-Type: application/json" -d "$data" --max-time 3600 "$url" >/dev/null 2>&1
  log "POST $url finished"
}

# Параметр $1 — тип запуска: full или partial
case "$1" in
  full)
    make_get "http://car-catch.ru:8080/update/dongchedi/full/"
    sleep 15
    make_get "http://car-catch.ru:8080/update/che168/full/"
    ;;
  partial)
    make_post "http://car-catch.ru:8080/update/dongchedi/" '{"last_n":10}'
    sleep 15
    make_post "http://car-catch.ru:8080/update/che168/" '{"last_n":10}'
    ;;
  *)
    log "Unknown parameter: $1"
    exit 1
    ;;
esac 