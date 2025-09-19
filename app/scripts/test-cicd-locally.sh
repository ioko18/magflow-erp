#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Local CI/CD Pipeline Test ===${NC}\n"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d ' ' -f 2)
if [[ ! "$PYTHON_VERSION" == 3.11* ]]; then
    echo -e "${YELLOW}Warning: Python 3.11 is recommended. Found Python $PYTHON_VERSION${NC}"
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Function to run a command and check its status
run_command() {
    echo -e "${YELLOW}Running: $1${NC}"
    eval $1
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error running: $1${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Success${NC}\n"
}

# Create a temporary directory for the test
TEMP_DIR=$(mktemp -d)
echo -e "Created temporary directory: ${GREEN}${TEMP_DIR}${NC}"

# Copy necessary files to the temp directory
echo -e "\n${YELLOW}Copying files...${NC}"
cp -r . ${TEMP_DIR}/
cd ${TEMP_DIR}

echo -e "Current directory: ${GREEN}$(pwd)${NC}"

# Step 1: Install dependencies
echo -e "\n${YELLOW}=== Step 1: Installing Dependencies ===${NC}"
run_command "python -m pip install --upgrade pip"
run_command "python -m pip install -r requirements.txt -r requirements-dev.txt"

# Step 2: Run tests
echo -e "\n${YELLOW}=== Step 2: Running Tests ===${NC}"
run_command "pytest tests/ -v --cov=app --cov-report=term-missing"

# Step 3: Build Docker image
echo -e "${YELLOW}=== Step 3: Building Docker Image ===${NC}"
DOCKER_IMAGE="magflow-local-test:$(date +%s)"
run_command "docker build -t ${DOCKER_IMAGE} ."

# Step 4: Test Docker container
echo -e "${YELLOW}=== Step 4: Testing Docker Container ===${NC}"
run_command "docker run -d -p 8000:8000 --name magflow-test ${DOCKER_IMAGE}"

# Wait for the container to start
sleep 5

# Check if the container is running
if ! docker ps | grep -q magflow-test; then
    echo -e "${RED}Container failed to start. Logs:${NC}"
    docker logs magflow-test
    exit 1
fi

# Test health endpoints
echo -e "\n${YELLOW}Testing health endpoints...${NC}"

check_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local max_retries=5
    local retry_count=0
    
    echo -n "Testing ${endpoint}... "
    
    while [ $retry_count -lt $max_retries ]; do
        status_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000${endpoint}")
        
        if [ "$status_code" -eq "$expected_status" ]; then
            echo -e "${GREEN}✓ ${status_code}${NC}"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        sleep 2
    done
    
    echo -e "${RED}✗ Expected ${expected_status}, got ${status_code}${NC}"
    return 1
}

check_endpoint "/api/v1/health/live" 200
check_endpoint "/api/v1/health/ready" 200
check_endpoint "/api/v1/health/startup" 200

# Step 5: Cleanup
echo -e "\n${YELLOW}=== Step 5: Cleaning Up ===${NC}"
run_command "docker stop magflow-test"
run_command "docker rm magflow-test"
run_command "docker rmi ${DOCKER_IMAGE}"

# Clean up temporary directory
cd ..
rm -rf "${TEMP_DIR}"

echo -e "\n${GREEN}=== Local CI/CD Test Completed Successfully ===${NC}"
echo -e "You can now push your changes to trigger the GitHub Actions workflow.\n"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. git add ."
echo "2. git commit -m 'Add CI/CD configuration'"
echo "3. git push"
echo -e "\nThen check the 'Actions' tab in your GitHub repository to monitor the workflow.\n"
