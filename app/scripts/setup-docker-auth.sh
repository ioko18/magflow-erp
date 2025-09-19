#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Docker Registry Setup Helper ===${NC}\n"

# Check if user is logged in to Docker
if ! docker info &> /dev/null; then
    echo "Docker is not running or you don't have permission to access it."
    exit 1
fi

# Check if gh is installed (for GitHub Container Registry)
if command -v gh &> /dev/null; then
    echo -e "GitHub CLI is installed. You can use GitHub Container Registry (ghcr.io)."
    USE_GHCR="y"
    read -p "Do you want to use GitHub Container Registry? (y/n) " USE_GHCR
    
    if [[ $USE_GHCR =~ ^[Yy]$ ]]; then
        echo -e "\n${YELLOW}=== GitHub Container Registry Setup ===${NC}"
        
        # Check if user is logged in to GitHub CLI
        if ! gh auth status &> /dev/null; then
            echo "You need to log in to GitHub CLI first. Running 'gh auth login'..."
            gh auth login
        fi
        
        # Get GitHub username
        GITHUB_USERNAME=$(gh api user --jq '.login')
        echo -e "\nYour GitHub username is: ${GREEN}${GITHUB_USERNAME}${NC}"
        
        # Create a fine-grained personal access token
        echo -e "\n${YELLOW}Creating a fine-grained personal access token...${NC}"
        echo "Please go to: https://github.com/settings/tokens/new"
        echo "Select your repository and set these permissions:"
        echo "- Repository permissions > Contents: Read and write"
        echo "- Repository permissions > Metadata: Read-only"
        echo "- Repository permissions > Packages: Read and write"
        echo -e "\nAfter creating the token, paste it below (it will not be displayed):"
        read -s GITHUB_TOKEN
        
        # Login to GitHub Container Registry
        echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
        
        # Update the Docker image name in the workflow
        sed -i '' "s|your-registry/magflow|ghcr.io/${GITHUB_USERNAME}/magflow|g" .github/workflows/ci-cd.yaml
        
        echo -e "\n${GREEN}GitHub Container Registry setup complete!${NC}"
        echo -e "Add the following secrets to your GitHub repository:"
        echo -e "REGISTRY_USERNAME: ${GREEN}${GITHUB_USERNAME}${NC}"
        echo -e "REGISTRY_PASSWORD: ${GREEN}${GITHUB_TOKEN}${NC} (the token you just created)"
        
        exit 0
    fi
fi

# Docker Hub setup
echo -e "\n${YELLOW}=== Docker Hub Setup ===${NC}"

read -p "Enter your Docker Hub username: " DOCKERHUB_USERNAME
read -s -p "Enter your Docker Hub password or access token: " DOCKERHUB_PASSWORD
echo ""

# Login to Docker Hub
echo $DOCKERHUB_PASSWORD | docker login -u $DOCKERHUB_USERNAME --password-stdin

# Update the Docker image name in the workflow
sed -i '' "s|your-registry/magflow|${DOCKERHUB_USERNAME}/magflow|g" .github/workflows/ci-cd.yaml

echo -e "\n${GREEN}Docker Hub setup complete!${NC}"
echo -e "Add the following secrets to your GitHub repository:"
echo -e "REGISTRY_USERNAME: ${GREEN}${DOCKERHUB_USERNAME}${NC}"
echo -e "REGISTRY_PASSWORD: ${GREEN}${DOCKERHUB_PASSWORD}${NC} (your Docker Hub password or access token)"

# Create a sample .dockerignore file if it doesn't exist
if [ ! -f .dockerignore ]; then
    echo -e "\n${YELLOW}Creating .dockerignore file...${NC}"
    cat > .dockerignore << 'EOF'
# Git
.git
.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Logs
logs/
*.log

# Local development
.env
.env.*
!.env.example

# Kubernetes
kubeconfig-*.yaml

# Secrets
**/*.pem
**/*.key
**/*.crt
**/*.p12
**/*.pfx
**/*.p7b
**/*.p7c
**/*.p7s
**/*.p10
**/*.spc
**/*.sst
**/*.stl
**/*.stl
**/*.jks
**/*.keystore
**/*.truststore

# Local development
.venv
.python-version

# Testing
.coverage
htmlcov/
.tox/
.nox/

# Jupyter Notebook
.ipynb_checkpoints

# macOS
.DS_Store
.AppleDouble
.LSOverride

# Windows
Thumbs.db
ehthumbs.db
Desktop.ini
$RECYCLE.BIN/

# Project specific
*.db
*.sqlite3
media/
staticfiles/
EOF

    echo -e "${GREEN}Created .dockerignore file${NC}"
fi
