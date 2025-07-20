FROM golang:1.24.5-alpine AS builder
WORKDIR /app
COPY . .
RUN go mod download
RUN go build -o datahub ./cmd/main.go

FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/datahub /app/datahub
EXPOSE 8080
CMD ["/app/datahub"] 