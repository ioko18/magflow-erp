#!/bin/sh
# Simple healthcheck for Prometheus

# Check if Prometheus is responding to HTTP requests
if wget --spider -S http://localhost:9090/-/healthy 2>&1 | grep -q "HTTP/.* 200"; then
    exit 0
else
    exit 1
fi
