#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== MagFlow Kubernetes Setup Helper ===${NC}\n"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "kubectl could not be found. Please install it first."
    exit 1
fi

# Get current context
CURRENT_CONTEXT=$(kubectl config current-context)
echo -e "Current Kubernetes context: ${GREEN}${CURRENT_CONTEXT}${NC}"
echo -e "${YELLOW}Make sure this is the correct cluster before proceeding!${NC}\n"

# Create namespaces if they don't exist
for NS in magflow-dev magflow-prod; do
    if ! kubectl get namespace $NS &> /dev/null; then
        echo -e "Creating namespace: ${GREEN}${NS}${NC}"
        kubectl create namespace $NS
    else
        echo -e "Namespace ${GREEN}${NS}${NC} already exists"
    fi
done

# Function to create kubeconfig file
create_kubeconfig() {
    local context=$1
    local output_file=$2
    
    echo -e "\n${YELLOW}Creating kubeconfig for ${context}...${NC}"
    
    # Get current cluster name
    local cluster_name=$(kubectl config view -o jsonpath="{.contexts[?(@.name==\"$context\")].context.cluster}")
    
    # Get cluster server
    local server=$(kubectl config view -o jsonpath="{.clusters[?(@.name==\"$cluster_name\")].cluster.server}")
    
    # Get certificate authority data
    local cert_auth=$(kubectl config view --raw -o jsonpath="{.clusters[?(@.name==\"$cluster_name\")].cluster.certificate-authority-data}")
    
    # Create kubeconfig
    cat > $output_file << EOF
apiVersion: v1
kind: Config
current-context: $context
contexts:
- name: $context
  context:
    cluster: $cluster_name
    user: github-actions
    namespace: magflow-${context##*-}
clusters:
- name: $cluster_name
  cluster:
    server: $server
    certificate-authority-data: $cert_auth
users:
- name: github-actions
  user:
    token: YOUR_SERVICE_ACCOUNT_TOKEN
EOF

    echo -e "${GREEN}Created kubeconfig file: ${output_file}${NC}"
    echo -e "${YELLOW}IMPORTANT: Replace 'YOUR_SERVICE_ACCOUNT_TOKEN' with an actual service account token before using this file.${NC}"
}

# Create kubeconfig files
create_kubeconfig "${CURRENT_CONTEXT}-dev" "kubeconfig-dev.yaml"
create_kubeconfig "${CURRENT_CONTEXT}-prod" "kubeconfig-prod.yaml"

# Create service accounts and roles
echo -e "\n${YELLOW}Creating service accounts and roles...${NC}"

# For development
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: github-actions
  namespace: magflow-dev
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: github-actions-role
  namespace: magflow-dev
rules:
- apiGroups: ["", "apps", "batch", "extensions"]
  resources: ["deployments", "services", "pods", "pods/exec", "pods/log", "jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: github-actions-role-binding
  namespace: magflow-dev
subjects:
- kind: ServiceAccount
  name: github-actions
  namespace: magflow-dev
roleRef:
  kind: Role
  name: github-actions-role
  apiGroup: rbac.authorization.k8s.io
EOF

# For production
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: github-actions
  namespace: magflow-prod
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: github-actions-role
  namespace: magflow-prod
rules:
- apiGroups: ["", "apps", "batch", "extensions"]
  resources: ["deployments", "services", "pods", "pods/exec", "pods/log", "jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: github-actions-role-binding
  namespace: magflow-prod
subjects:
- kind: ServiceAccount
  name: github-actions
  namespace: magflow-prod
roleRef:
  kind: Role
  name: github-actions-role
  apiGroup: rbac.authorization.k8s.io
EOF

# Get tokens for service accounts
echo -e "\n${YELLOW}Service Account Tokens:${NC}"
echo -e "${GREEN}Development token:${NC}"
kubectl -n magflow-dev get secret $(kubectl -n magflow-dev get serviceaccount github-actions -o jsonpath='{.secrets[0].name}') -o jsonpath='{.data.token}' | base64 --decode
echo -e "\n${GREEN}Production token:${NC}"
kubectl -n magflow-prod get secret $(kubectl -n magflow-prod get serviceaccount github-actions -o jsonpath='{.secrets[0].name}') -o jsonpath='{.data.token}' | base64 --decode

echo -e "\n${YELLOW}=== Next Steps ===${NC}"
echo "1. Replace 'YOUR_SERVICE_ACCOUNT_TOKEN' in the generated kubeconfig files with the tokens above"
echo "2. Add the following secrets to your GitHub repository:"
echo "   - REGISTRY_USERNAME: Your Docker Hub or GitHub username"
echo "   - REGISTRY_PASSWORD: Your Docker Hub token or GitHub Personal Access Token"
echo "   - KUBE_CONFIG_DEV: Contents of kubeconfig-dev.yaml (base64 encoded)"
echo "   - KUBE_CONFIG_PROD: Contents of kubeconfig-prod.yaml (base64 encoded)"
echo -e "\nTo base64 encode the kubeconfig files, run:"
echo "cat kubeconfig-dev.yaml | base64 | pbcopy"
echo "cat kubeconfig-prod.yaml | base64 | pbcopy"

echo -e "\n${GREEN}Setup complete!${NC}"
