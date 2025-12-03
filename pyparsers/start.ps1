.venv/Scripts/Activate.ps1

# Load environment variables
if (Test-Path "../.env") {
    Get-Content "../.env" | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

# Get configuration from environment variables
$API_HOST = $env:API_HOST
if (-not $API_HOST) { $API_HOST = "0.0.0.0" }

$API_PORT = $env:API_PORT
if (-not $API_PORT) { $API_PORT = "8000" }

# Start the server with HTTP/1 keep-alive enabled
# Note: granian doesn't support --reload flag, use watchfiles or similar for development
granian --interface asgi --host $API_HOST --port $API_PORT --http1-keep-alive async_api_server:app
