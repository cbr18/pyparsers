# CarCatch - Car Parser System

Микросервисная система для парсинга, хранения и отображения информации об автомобилях с китайских сайтов dongchedi.com и che168.com.

## 🚀 Quick Start

```bash
# Clone repository
git clone <repository>
cd CarsParser

# Start all services
docker-compose up -d

# Check health
./scripts/health-check.ps1  # Windows
./scripts/health-check.sh   # Linux/Mac
```

## 🌐 Access Applications

- **Main App:** http://localhost/podbortg
- **Angular App:** http://localhost/ng
- **API Documentation:** http://localhost/docs
- **Swagger UI:** http://localhost/swagger
- **Development API:** http://localhost:8000

## 📋 Basic Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Build and start
docker-compose up -d --build
```

## 🏗️ Architecture

- **nginx** (80, 443) - Reverse proxy
- **datahub** (8080) - Main API (Go)
- **pyparsers** (5000) - Car parsing (Python)
- **telegrambot** (3001) - Telegram bot (Node.js)
- **telegramapp** (3002) - React web app
- **telegramngapp** (3003) - Angular web app
- **postgres** (5432) - Database

## 📚 Documentation

- [API Documentation](docs/API_DOCUMENTATION.md) - Complete API reference
- [API Examples](docs/API_EXAMPLES.md) - Usage examples
- [Deployment Guide](DEPLOYMENT.md) - Detailed setup instructions

## 🔧 Development

The system is configured for development by default with:
- Debug logging enabled
- Database port exposed
- Hot reload support
- CORS enabled

## 🐛 Troubleshooting

```bash
# Check service status
docker-compose ps

# View specific service logs
docker-compose logs datahub
docker-compose logs pyparsers

# Restart specific service
docker-compose restart nginx

# Clean up and restart
docker-compose down -v
docker-compose up -d --build
```

## 📊 Health Monitoring

Use the health check scripts to monitor all services:

```bash
# Windows
./scripts/health-check.ps1

# Linux/Mac
./scripts/health-check.sh
```

## 🗄️ Database Operations

```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres carsdb > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres carsdb < backup.sql

# Access database
docker-compose exec postgres psql -U postgres carsdb
```

 
