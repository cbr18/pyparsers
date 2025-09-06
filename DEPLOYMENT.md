# CarCatch Deployment Guide

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git
- Make (optional, for convenience commands)

### Development Setup

1. **Clone and start services:**
```bash
git clone <repository>
cd CarsParser
docker-compose up -d
```

3. **Access applications:**
- Main App: http://localhost/podbortg
- Angular App: http://localhost/ng
- API Documentation: http://localhost/docs
- Swagger UI: http://localhost/swagger
- Development API: http://localhost:8000

### Production Setup

1. **Configure environment:**
```bash
cp .env .env.production
# Edit .env.production with production values (secure passwords, etc.)
```

2. **Start services:**
```bash
docker-compose up -d
```

## Service Architecture

### Core Services
- **nginx** (80, 443) - Reverse proxy and load balancer
- **datahub** (8080) - Main API service (Go)
- **pyparsers** (5000) - Car parsing service (Python)
- **postgres** (5432) - Database
- **telegrambot** (3001) - Telegram bot service

### Frontend Services
- **telegramapp** (3002) - React web application
- **telegramngapp** (3003) - Angular web application

### Background Services
- **cron-updater** - Scheduled data updates

## Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=carsdb
POSTGRES_HOST=postgres

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
LEAD_TARGET_CHAT=@your_chat

# API URLs (Docker internal)
API_BASE_URL=http://pyparsers:5000
LOCAL_API_URL=http://datahub:8080

# Frontend
REACT_APP_API_URL=/api
ANGULAR_API_URL=/api
```

### SSL/HTTPS Setup

1. **Obtain SSL certificates:**
```bash
# Using Let's Encrypt
sudo certbot certonly --webroot -w /var/www/html -d car-catch.ru -d www.car-catch.ru
```

2. **Update nginx.conf paths:**
```nginx
ssl_certificate /etc/letsencrypt/live/car-catch.ru/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/car-catch.ru/privkey.pem;
```

## Available Commands

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Restart all services
docker-compose restart

# Individual services
docker-compose up -d nginx datahub
docker-compose restart pyparsers
docker-compose logs -f datahub

# Build and start
docker-compose up -d --build

# Clean up
docker-compose down -v --remove-orphans
```

## Health Monitoring

### Automated Health Checks

```bash
# Linux/Mac
./scripts/health-check.sh

# Windows
./scripts/health-check.ps1
```

### Manual Health Checks

```bash
# Check all containers
docker-compose ps

# Check specific service
curl http://localhost/health
curl http://localhost:8080/cars
curl http://localhost:5000/health

# Check database
docker-compose exec postgres pg_isready -U postgres
```

### Service URLs

- **Main Application:** http://localhost/podbortg
- **Angular App:** http://localhost/ng
- **API Documentation:** http://localhost/docs
- **Swagger UI:** http://localhost/swagger
- **Development API:** http://localhost:8000

Direct service access:
- **DataHub:** http://localhost:8080
- **PyParsers:** http://localhost:5000
- **Telegram Bot:** http://localhost:3001
- **React App:** http://localhost:3002
- **Angular App:** http://localhost:3003

## Troubleshooting

### Common Issues

1. **Port conflicts:**
```bash
# Check what's using ports
netstat -tulpn | grep :80
netstat -tulpn | grep :443

# Stop conflicting services
sudo systemctl stop apache2
sudo systemctl stop nginx
```

2. **Database connection issues:**
```bash
# Check database logs
docker-compose logs postgres

# Reset database
make db-reset

# Manual database connection
docker-compose exec postgres psql -U postgres -d carsdb
```

3. **SSL certificate issues:**
```bash
# Check certificate validity
openssl x509 -in /etc/letsencrypt/live/car-catch.ru/fullchain.pem -text -noout

# Renew certificates
sudo certbot renew
```

4. **Service not responding:**
```bash
# Check service logs
docker-compose logs service_name

# Restart specific service
docker-compose restart service_name

# Rebuild and restart
docker-compose build service_name
docker-compose up -d service_name
```

### Performance Issues

1. **High memory usage:**
```bash
# Check resource usage
docker stats

# Limit resources (in docker-compose.prod.yml)
deploy:
  resources:
    limits:
      memory: 1G
```

2. **Slow API responses:**
```bash
# Check nginx cache
curl -I http://localhost/cars
# Look for X-Cache-Status header

# Check database performance
docker-compose exec postgres psql -U postgres -d carsdb -c "SELECT * FROM pg_stat_activity;"
```

### Logs and Debugging

```bash
# All logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f datahub
docker-compose logs -f pyparsers

# Follow logs with timestamps
docker-compose logs -f -t

# Last 100 lines
docker-compose logs --tail=100
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U postgres carsdb > backup_$(date +%Y%m%d_%H%M%S).sql

# Or with compression
docker-compose exec postgres pg_dump -U postgres carsdb | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Database Restore

```bash
# Restore from backup
docker-compose exec -T postgres psql -U postgres carsdb < backup.sql

# Or from compressed backup
gunzip -c backup.sql.gz | docker-compose exec -T postgres psql -U postgres carsdb
```

### Full System Backup

```bash
# Backup volumes
docker run --rm -v carcatch_pg_data:/data -v $(pwd):/backup alpine tar czf /backup/pg_data_backup.tar.gz -C /data .

# Backup configuration
tar czf config_backup.tar.gz .env nginx.conf docker-compose.yml
```

## Security Considerations

### Production Security

1. **Change default passwords:**
```bash
# Generate secure password
openssl rand -base64 32

# Update .env file
POSTGRES_PASSWORD=your_secure_password
```

2. **Firewall configuration:**
```bash
# Allow only necessary ports
sudo ufw allow 80
sudo ufw allow 443
sudo ufw deny 5432  # Block direct database access
```

3. **Regular updates:**
```bash
# Update system
sudo apt update && sudo apt upgrade

# Update Docker images
docker-compose pull
docker-compose up -d
```

4. **Monitor logs:**
```bash
# Check for suspicious activity
docker-compose logs nginx | grep -E "(404|500|error)"
```

## Scaling

### Horizontal Scaling

```bash
# Scale specific services
docker-compose up -d --scale datahub=3 --scale telegramapp=2

# Using production config with replicas
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Load Balancing

The nginx configuration includes upstream definitions for load balancing:

```nginx
upstream datahub_backend {
    server datahub:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

## Monitoring and Alerting

### Basic Monitoring

```bash
# Resource usage
docker stats

# Service status
./scripts/health-check.ps1  # Windows
./scripts/health-check.sh   # Linux/Mac

# Continuous monitoring
watch -n 5 'docker-compose ps && echo "" && docker stats --no-stream'
```

### Advanced Monitoring

Consider integrating:
- **Prometheus + Grafana** for metrics
- **ELK Stack** for log analysis
- **Uptime monitoring** services
- **Alert manager** for notifications

## Support

For issues and questions:
1. Check the logs: `make logs`
2. Run health check: `make health`
3. Review this documentation
4. Check the API documentation: http://localhost/docs
