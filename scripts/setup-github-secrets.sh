#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) is not installed. Please install it first."
    echo "Visit: https://cli.github.com/"
    exit 1
fi

# Check if user is logged in to GitHub CLI
if ! gh auth status &> /dev/null; then
    echo "You need to log in to GitHub CLI first. Running 'gh auth login'..."
    gh auth login
fi

# Get repository info
REPO_OWNER=$(gh repo view --json owner --jq '.owner.login')
REPO_NAME=$(gh repo view --json name --jq '.name')
REPO_FULL_NAME="${REPO_OWNER}/${REPO_NAME}"

echo -e "${YELLOW}=== GitHub Repository Secrets Setup for ${REPO_FULL_NAME} ===${NC}\n"

# Function to set a secret
set_secret() {
    local secret_name=$1
    local secret_value=$2
    
    echo -e "Setting secret: ${YELLOW}${secret_name}${NC}"
    
    if [ -z "$secret_value" ]; then
        echo -n "Enter value for ${secret_name} (input hidden): "
        read -s secret_value
        echo ""
    fi
    
    # Check if secret already exists
    if gh secret list | grep -q "${secret_name}"; then
        read -p "Secret ${secret_name} already exists. Update? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    # Set the secret
    echo "${secret_value}" | gh secret set "${secret_name}" --repo "${REPO_FULL_NAME}"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Set secret: ${secret_name}${NC}"
    else
        echo -e "${YELLOW}✗ Failed to set secret: ${secret_name}${NC}"
    fi
    echo
}

# Get base64 encoded kubeconfigs
if [ -f "kubeconfig-dev.yaml" ]; then
    KUBE_CONFIG_DEV=$(cat kubeconfig-dev.yaml | base64)
    set_secret "KUBE_CONFIG_DEV" "$KUBE_CONFIG_DEV"
else
    echo -e "${YELLOW}Warning: kubeconfig-dev.yaml not found. Skipping KUBE_CONFIG_DEV.${NC}"
fi

if [ -f "kubeconfig-prod.yaml" ]; then
    KUBE_CONFIG_PROD=$(cat kubeconfig-prod.yaml | base64)
    set_secret "KUBE_CONFIG_PROD" "$KUBE_CONFIG_PROD"
else
    echo -e "${YELLOW}Warning: kubeconfig-prod.yaml not found. Skipping KUBE_CONFIG_PROD.${NC}"
fi

# Set Docker registry credentials
read -p "Do you want to set Docker registry credentials? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter Docker registry username: " DOCKER_USERNAME
    read -s -p "Enter Docker registry password/token: " DOCKER_PASSWORD
    echo
    
    set_secret "REGISTRY_USERNAME" "$DOCKER_USERNAME"
    set_secret "REGISTRY_PASSWORD" "$DOCKER_PASSWORD"
fi

# Set other common secrets
read -p "Do you want to set other common secrets? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    set_secret "CODECOV_TOKEN" ""
    set_secret "SLACK_WEBHOOK_URL" ""
    set_secret "SENTRY_DSN" ""
fi

echo -e "\n${GREEN}=== Secrets Setup Complete ===${NC}"
echo -e "You can view and manage your secrets at:"
echo -e "https://github.com/${REPO_OWNER}/${REPO_NAME}/settings/secrets/actions\n"

echo -e "${YELLOW}=== Next Steps ===${NC}"
echo "1. Push your changes to trigger the CI/CD pipeline:"
echo "   git add ."
echo "   git commit -m 'Add CI/CD configuration'"
echo "   git push"
echo -e "\n2. Monitor the workflow run in the 'Actions' tab of your repository."
echo -e "\n3. Check the deployment status:"
echo "   kubectl get pods -n magflow-dev"
echo -e "\n4. (Optional) Set up a custom domain and TLS certificates for production."
