FROM golang:1.24.5-alpine AS builder
WORKDIR /app
COPY . .
RUN go mod download
RUN go build -o datahub ./cmd/main.go

# Install migrate in builder stage
RUN go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

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
