#!/bin/bash

# PyParsers Health Check Script
# This script checks the split parser services

set -e

echo "🏥 PyParsers Health Check"
echo "========================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check HTTP endpoint
check_http() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    echo -n "Checking $name... "

    if response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_code" ]; then
            echo -e "${GREEN}✅ Healthy${NC} (HTTP $response)"
        else
            echo -e "${YELLOW}⚠️  Warning${NC} (HTTP $response, expected $expected_code)"
        fi
    else
        echo -e "${RED}❌ Failed${NC} (Connection failed)"
    fi
}

# Function to check Docker container
check_container() {
    local name=$1
    local container_name=$2

    echo -n "Checking $name container... "

    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*Up"; then
        echo -e "${GREEN}✅ Running${NC}"
    else
        echo -e "${RED}❌ Not running${NC}"
    fi
}

echo "🐳 Docker Containers:"
echo "--------------------"
check_container "PyParsers Dongchedi" "carcatch-pyparsers-dongchedi"
check_container "PyParsers Che168" "carcatch-pyparsers-che168"

echo ""
echo "🌐 HTTP Endpoints:"
echo "------------------"
check_http "PyParsers Dongchedi API" "http://localhost:5001/health"
check_http "PyParsers Che168 API" "http://localhost:5002/health"

echo ""
echo "📊 Parser Endpoints:"
echo "-------------"
check_http "Dongchedi List" "http://localhost:5001/cars/dongchedi/page/1"
check_http "Che168 Docs" "http://localhost:5002/docs"

echo ""
echo "📈 Service Statistics:"
echo "---------------------"
echo "Docker containers running: $(docker ps --format "table {{.Names}}" | grep -c carcatch || echo 0)"
echo "Docker images: $(docker images | grep -c carcatch || echo 0)"
echo "Docker volumes: $(docker volume ls | grep -c carcatch || echo 0)"

# Check disk usage
echo "Disk usage:"
df -h / | tail -1 | awk '{print "  Root: " $3 "/" $2 " (" $5 " used)"}'

# Check memory usage
echo "Memory usage:"
free -h | grep Mem | awk '{print "  RAM: " $3 "/" $2 " (" int($3/$2*100) "% used)"}'

echo ""
echo "✅ Health check completed!"
echo ""
echo "🔗 Quick Links:"
echo "  Dongchedi Docs: http://localhost:5001/docs"
echo "  Che168 Docs: http://localhost:5002/docs"
