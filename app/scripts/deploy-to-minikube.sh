#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Deploying MagFlow to Minikube ===${NC}\n"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required commands
for cmd in docker kubectl minikube; do
    if ! command_exists "$cmd"; then
        echo -e "${RED}Error: $cmd is not installed. Please install it and try again.${NC}"
        exit 1
    fi
done

# Set the Docker environment to use Minikube's Docker daemon
echo -e "${YELLOW}Configuring Docker to use Minikube's Docker daemon...${NC}"
eval $(minikube docker-env)

# Build the Docker image using the simplified Dockerfile
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -f Dockerfile.simple -t magflow:latest .

# Check if the build was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Docker build failed. Please check the error messages above.${NC}"
    exit 1
fi

# Create Kubernetes resources
echo -e "\n${YELLOW}Creating Kubernetes resources...${NC}"

# Apply the Kubernetes manifests
kubectl apply -f deploy/k8s/base/
kubectl apply -f deploy/k8s/overlays/development/

# Wait for the deployment to be ready
echo -e "\n${YELLOW}Waiting for the deployment to be ready...${NC}"
kubectl rollout status deployment/magflow -n magflow-dev --timeout=120s

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Deployment failed to become ready.${NC}"
    echo -e "${YELLOW}Checking pod status...${NC}"
    kubectl get pods -n magflow-dev
    exit 1
fi

# Get the Minikube IP
MINIKUBE_IP=$(minikube ip)

# Update /etc/hosts if we have permission
echo -e "\n${YELLOW}To access the application, add the following to your /etc/hosts file:${NC}"
echo "${MINIKUBE_IP} magflow-dev.local"
echo -e "\n${YELLOW}Or run the following command (requires sudo):${NC}"
echo "echo \"${MINIKUBE_IP} magflow-dev.local\" | sudo tee -a /etc/hosts"

# Set up port forwarding
echo -e "\n${YELLOW}Setting up port forwarding...${NC}"
echo -e "${GREEN}Access the application at: http://localhost:8000${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop port forwarding${NC}"
kubectl port-forward -n magflow-dev svc/magflow 8000:80
