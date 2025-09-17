#!/bin/bash

# Test script for image proxy functionality
echo "Testing image proxy functionality..."

# Test with a sample external image URL
TEST_URL="https://autoimg.cn/example.jpg"
ENCODED_URL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$TEST_URL'))")

echo "Original URL: $TEST_URL"
echo "Encoded URL: $ENCODED_URL"
echo "Proxy URL: http://localhost/proxy-image/$ENCODED_URL"

# Test the proxy endpoint
echo ""
echo "Testing proxy endpoint..."
curl -I "http://localhost/proxy-image/$ENCODED_URL" 2>/dev/null | head -5

echo ""
echo "Test completed. Check the response headers above."
