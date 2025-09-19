#!/bin/bash

# Test traffic generator for MagFlow ERP system
# This script generates test traffic to trigger alerts in Prometheus and Alertmanager

# Base URL for the API
BASE_URL="http://localhost:8000/api/v1/test/test"

# Function to make a request with a random delay
make_request() {
    local endpoint=$1
    local method=${2:-GET}
    local data=""
    
    # For POST requests, add JSON data
    if [[ "$method" == "POST" ]]; then
        if [[ "$endpoint" == "/latency" ]]; then
            local delay_ms=$((RANDOM % 1000))  # Random delay up to 1 second
            data="-d {\"delay_ms\": $delay_ms}"
        else
            data="-d {}"
        fi
    fi
    
    # Make the request and capture the status code
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" -X $method $data "${BASE_URL}${endpoint}")
    echo "$method ${endpoint} - Status: $response"
}

# Function to generate normal traffic
generate_normal_traffic() {
    echo "Generating normal traffic..."
    for i in {1..20}; do
        make_request "/health" "GET"
        sleep 0.5
    done
}

# Function to generate high latency traffic
generate_high_latency_traffic() {
    echo "Generating high latency traffic..."
    for i in {1..10}; do
        make_request "/latency" "POST"
        sleep 0.5
    done
}

# Function to generate error traffic
generate_error_traffic() {
    echo "Generating error traffic..."
    for i in {1..10}; do
        make_request "/error" "GET"
        sleep 0.5
    done
}

# Function to generate specific error traffic
generate_specific_error_traffic() {
    echo "Generating specific error traffic..."
    for status_code in 400 401 403 404 500 502 503 504; do
        make_request "/error/${status_code}" "GET"
        sleep 0.5
    done
}

# Main execution
echo "Starting test traffic generation..."

# Generate normal traffic
generate_normal_traffic

# Generate high latency traffic
generate_high_latency_traffic

# Generate error traffic
generate_error_traffic

# Generate specific error traffic
generate_specific_error_traffic

echo "Test traffic generation completed."
