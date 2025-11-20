FROM golang:1.25.4-alpine AS builder
WORKDIR /app

# Install migrate
RUN go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

FROM alpine:3.19
RUN apk --no-cache add ca-certificates postgresql-client
WORKDIR /app

# Copy migrate binary
COPY --from=builder /go/bin/migrate /app/migrate

# Copy migration files
COPY ./migrations /app/migrations

# Copy wait script
COPY ./wait-for-db.sh /app/wait-for-db.sh
RUN chmod +x /app/wait-for-db.sh

# Migration script
COPY ./run-migrations.sh /app/run-migrations.sh
RUN chmod +x /app/run-migrations.sh

CMD ["/app/run-migrations.sh"]
