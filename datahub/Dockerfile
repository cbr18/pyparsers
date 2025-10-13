FROM golang:1.24.5-alpine AS builder
WORKDIR /app

# 1) Кэшируем зависимости отдельно, чтобы не перекачивать их при каждом изменении кода
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go mod download

# 2) Копируем остальной исходный код и собираем бинарник с кэшами сборки
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /app/datahub ./cmd/main.go

# 3) Устанавливаем migrate (пинованный тег), слой кешируется отдельно
RUN --mount=type=cache,target=/go/pkg/mod \
    go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@v4.17.1

FROM alpine:3.19
RUN apk --no-cache add ca-certificates postgresql-client
WORKDIR /app

# Copy the built application
COPY --from=builder /app/datahub /app/datahub

# Copy migrate binary
COPY --from=builder /go/bin/migrate /app/migrate

# Copy migration files
COPY ./migrations /app/migrations

# Copy wait script
COPY ./wait-for-db.sh /app/wait-for-db.sh
RUN chmod +x /app/wait-for-db.sh

EXPOSE 8080
CMD ["/app/datahub"]
