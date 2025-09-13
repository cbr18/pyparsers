FROM golang:1.24.5-alpine AS builder
WORKDIR /app
COPY . .
RUN go mod download
RUN go build -o datahub ./cmd/main.go

# Install migrate in builder stage
RUN go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# Install Atlas CLI
RUN go install ariga.io/atlas/cmd/atlas@latest

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /app

# Copy the built application
COPY --from=builder /app/datahub /app/datahub
# Copy migrate binary from correct location
COPY --from=builder /go/bin/migrate /app/migrate
# Copy atlas binary from correct location
COPY --from=builder /go/bin/atlas /app/atlas

# Copy migration files
COPY ./migrations /app/migrations

EXPOSE 8080
CMD ["/app/datahub"]