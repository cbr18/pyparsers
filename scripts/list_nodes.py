#!/usr/bin/env python3
import subprocess
import json
import sys
import re
import os

def get_server_ip():
    # Try to get public IP first
    try:
        import urllib.request
        with urllib.request.urlopen("https://icanhazip.com", timeout=2) as response:
            return response.read().decode("utf-8").strip()
    except Exception:
        pass

    # Fallback to local primary interface IP
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # doesn't even have to be reachable
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def get_compose_status():
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        if not result.stdout.strip():
            return []
        
        # docker compose ps --format json returns multiple JSON objects (NDJSON)
        lines = result.stdout.strip().split("\n")
        statuses = []
        for line in lines:
            if line:
                statuses.append(json.loads(line))
        return statuses
    except Exception as e:
        print(f"Error getting docker status: {e}", file=sys.stderr)
        return []

def main():
    ip = get_server_ip()
    statuses = get_compose_status()
    
    # Map service names from docker-compose.yml to their display info
    nodes_config = {
        "pyparsers-dongchedi": {
            "source": "dongchedi",
            "name": "dongchedi pyparsers server",
            "port": 5001,
            "priority": 10
        },
        "pyparsers-che168": {
            "source": "che168",
            "name": "che168 pyparsers server",
            "port": 5002,
            "priority": 30
        },
        "pyparsers-encar": {
            "source": "encar",
            "name": "encar pyparsers server",
            "port": 5003,
            "priority": 20
        }
    }
    
    # Track which services we found
    running_services = {s["Service"]: s for s in statuses if s["State"] == "running"}
    
    output = []
    inactive = []
    
    for service_id, config in nodes_config.items():
        is_active = service_id in running_services
        node = {
            "source": config["source"],
            "name": config["name"],
            "baseUrl": f"http://{ip}:{config['port']}",
            "isActive": is_active,
            "priority": config["priority"]
        }
        output.append(node)
        if not is_active:
            inactive.append(config["source"])
            
    # Print warning to stderr if any node is inactive
    if inactive:
        print(f"Warning: The following nodes are NOT running: {', '.join(inactive)}", file=sys.stderr)
        
    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
