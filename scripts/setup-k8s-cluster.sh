#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Kubernetes Cluster Setup for MagFlow CI/CD ===${NC}\n"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}kubectl is not installed. Please install it first.${NC}"
    echo "Visit: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check if helm is installed
if ! command -v helm &> /dev/null; then
    echo -e "${YELLOW}Helm is not installed. Would you like to install it? (y/n)${NC}"
    read -r INSTALL_HELM
    if [[ $INSTALL_HELM =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Installing Helm...${NC}"
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    else
        echo -e "${YELLOW}Helm is required for some features. Continuing without Helm.${NC}"
    fi
fi

# Function to create a Kubernetes namespace if it doesn't exist
create_namespace() {
    local namespace=$1
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        echo -e "${YELLOW}Creating namespace: ${namespace}${NC}"
        kubectl create namespace "$namespace"
        kubectl label namespace "$namespace" "app.kubernetes.io/name"="magflow"
        echo -e "${GREEN}✓ Created namespace: ${namespace}${NC}\n"
    else
        echo -e "${GREEN}✓ Namespace ${namespace} already exists${NC}\n"
    fi
}

# Function to create a service account with RBAC
create_service_account() {
    local namespace=$1
    local sa_name="github-actions"
    
    echo -e "${YELLOW}Creating service account in namespace: ${namespace}${NC}"
    
    # Create service account
    kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${sa_name}
  namespace: ${namespace}
  labels:
    app.kubernetes.io/name: magflow
    app.kubernetes.io/instance: github-actions
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: github-actions-role
  namespace: ${namespace}
rules:
- apiGroups: ["", "apps", "batch", "extensions"]
  resources: ["deployments", "pods", "services", "configmaps", "secrets", "ingresses", "cronjobs", "jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: github-actions-role-binding
  namespace: ${namespace}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: github-actions-role
subjects:
- kind: ServiceAccount
  name: ${sa_name}
  namespace: ${namespace}
EOF
    
    echo -e "${GREEN}✓ Created service account: ${sa_name} in namespace: ${namespace}${NC}\n"
    
    # Get the service account token
    local secret_name=$(kubectl get serviceaccount ${sa_name} -n ${namespace} -o jsonpath='{.secrets[0].name}')
    local token=$(kubectl get secret ${secret_name} -n ${namespace} -o jsonpath='{.data.token}' | base64 --decode)
    
    echo -e "${YELLOW}Service Account Token for ${namespace}:${NC}"
    echo -e "${GREEN}${token}${NC}\n"
    
    # Create kubeconfig file
    local context_name=$(kubectl config current-context)
    local cluster_name=$(kubectl config view -o jsonpath="{.contexts[?(@.name==\"${context_name}\")].context.cluster}")
    local server_url=$(kubectl config view -o jsonpath="{.clusters[?(@.name==\"${cluster_name}\")].cluster.server}")
    
    # Create kubeconfig file
    KUBECONFIG_FILE="kubeconfig-${namespace}.yaml"
    
    kubectl config set-cluster ${cluster_name} \
      --kubeconfig=${KUBECONFIG_FILE} \
      --server=${server_url} \
      --certificate-authority=/etc/kubernetes/pki/ca.crt \
      --embed-certs=true \
      --dry-run=client -o yaml > ${KUBECONFIG_FILE}
    
    kubectl config set-credentials github-actions-${namespace} \
      --kubeconfig=${KUBECONFIG_FILE} \
      --token=${token} \
      --dry-run=client -o yaml >> ${KUBECONFIG_FILE}
    
    kubectl config set-context github-actions-${namespace} \
      --kubeconfig=${KUBECONFIG_FILE} \
      --cluster=${cluster_name} \
      --user=github-actions-${namespace} \
      --namespace=${namespace} \
      --dry-run=client -o yaml >> ${KUBECONFIG_FILE}
    
    kubectl config use-context github-actions-${namespace} \
      --kubeconfig=${KUBECONFIG_FILE} \
      --dry-run=client -o yaml >> ${KUBECONFIG_FILE}
    
    echo -e "${GREEN}✓ Created kubeconfig file: ${KUBECONFIG_FILE}${NC}"
    echo -e "${YELLOW}Add this file as a GitHub secret named KUBE_CONFIG_${namespace^^}${NC}\n"
}

# Create namespaces
create_namespace "magflow-dev"
create_namespace "magflow-prod"

# Create service accounts and RBAC
create_service_account "magflow-dev"
create_service_account "magflow-prod"

# Create a sample secret for the application
create_secret() {
    local namespace=$1
    local secret_name="magflow-secrets"
    
    echo -e "${YELLOW}Creating sample secret in namespace: ${namespace}${NC}"
    
    kubectl create secret generic ${secret_name} \
      --namespace=${namespace} \
      --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
      --from-literal=DB_PASSWORD=$(openssl rand -hex 16) \
      --dry-run=client -o yaml | kubectl apply -f -
    
    echo -e "${GREEN}✓ Created secret: ${secret_name} in namespace: ${namespace}${NC}\n"
}

create_secret "magflow-dev"
create_secret "magflow-prod"

# Create a sample configmap
create_configmap() {
    local namespace=$1
    local configmap_name="magflow-config"
    
    echo -e "${YELLOW}Creating sample configmap in namespace: ${namespace}${NC}"
    
    kubectl create configmap ${configmap_name} \
      --namespace=${namespace} \
      --from-literal=APP_ENV=${namespace##*-} \
      --from-literal=LOG_LEVEL=INFO \
      --dry-run=client -o yaml | kubectl apply -f -
    
    echo -e "${GREEN}✓ Created configmap: ${configmap_name} in namespace: ${namespace}${NC}\n"
}

create_configmap "magflow-dev"
create_configmap "magflow-prod"

# Install ingress-nginx if not installed
if ! kubectl get pods -n ingress-nginx &> /dev/null; then
    echo -e "${YELLOW}Installing ingress-nginx...${NC}"
    
    if command -v helm &> /dev/null; then
        # Install with Helm
        helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
        helm repo update
        helm install ingress-nginx ingress-nginx/ingress-nginx \
          --namespace ingress-nginx \
          --create-namespace \
          --set controller.publishService.enabled=true \
          --set controller.service.type=LoadBalancer
    else
        # Install with kubectl
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.2.0/deploy/static/provider/cloud/deploy.yaml
    fi
    
    echo -e "${GREEN}✓ Installed ingress-nginx${NC}\n"
else
    echo -e "${GREEN}✓ ingress-nginx is already installed${NC}\n"
fi

# Install cert-manager if not installed
if ! kubectl get pods -n cert-manager &> /dev/null; then
    echo -e "${YELLOW}Installing cert-manager...${NC}"
    
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.10.1/cert-manager.yaml
    
    echo -e "${GREEN}✓ Installed cert-manager${NC}\n"
    
    # Wait for cert-manager to be ready
    echo -e "${YELLOW}Waiting for cert-manager to be ready...${NC}"
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
    
    # Create ClusterIssuer for Let's Encrypt
    echo -e "${YELLOW}Creating Let's Encrypt ClusterIssuer...${NC}"
    
    kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com  # Change this to your email
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@example.com  # Change this to your email
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
    
    echo -e "${GREEN}✓ Created Let's Encrypt ClusterIssuers${NC}\n"
else
    echo -e "${GREEN}✓ cert-manager is already installed${NC}\n"
fi

echo -e "${GREEN}=== Kubernetes Cluster Setup Complete ===${NC}\n"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Add the kubeconfig files as GitHub secrets:"
echo "   - KUBE_CONFIG_MAGFLOW_DEV: $(cat kubeconfig-magflow-dev.yaml | base64 | tr -d '\n')"
echo "   - KUBE_CONFIG_MAGFLOW_PROD: $(cat kubeconfig-magflow-prod.yaml | base64 | tr -d '\n')"
echo -e "\n2. Push your changes to trigger the CI/CD pipeline:"
echo "   git add ."
echo "   git commit -m 'Add Kubernetes configuration'"
echo "   git push"
echo -e "\n3. Monitor the deployment in the 'Actions' tab of your GitHub repository.\n"

echo -e "${GREEN}Your Kubernetes cluster is now ready for MagFlow CI/CD!${NC}\n"
