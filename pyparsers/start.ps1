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

$API_RELOAD = $env:API_RELOAD
if (-not $API_RELOAD) { $API_RELOAD = "true" }

# Start the server
uvicorn api_server:app --host $API_HOST --port $API_PORT --reload
