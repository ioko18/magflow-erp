#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Minikube Setup for MagFlow ===${NC}\n"

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

# Enable required Minikube addons
echo -e "${YELLOW}Enabling Minikube addons...${NC}"
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable dashboard

echo -e "${GREEN}✓ Minikube addons enabled${NC}\n"

# Create namespaces
create_namespace "magflow-dev"
create_namespace "magflow-prod"

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

# Create a sample deployment
create_deployment() {
    local namespace=$1
    
    echo -e "${YELLOW}Creating sample deployment in namespace: ${namespace}${NC}"
    
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: magflow
  namespace: ${namespace}
  labels:
    app: magflow
    env: ${namespace##*-}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: magflow
      env: ${namespace##*-}
  template:
    metadata:
      labels:
        app: magflow
        env: ${namespace##*-}
    spec:
      containers:
      - name: magflow
        image: nginx:alpine
        ports:
        - containerPort: 80
        envFrom:
        - configMapRef:
            name: magflow-config
        - secretRef:
            name: magflow-secrets
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: magflow
  namespace: ${namespace}
  labels:
    app: magflow
    env: ${namespace##*-}
spec:
  selector:
    app: magflow
    env: ${namespace##*-}
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: magflow
  namespace: ${namespace}
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: magflow-${namespace##*-}.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: magflow
            port:
              number: 80
EOF

    echo -e "${GREEN}✓ Created deployment in namespace: ${namespace}${NC}"
    echo -e "${YELLOW}Access URL: http://magflow-${namespace##*-}.local${NC}\n"
}

create_deployment "magflow-dev"
create_deployment "magflow-prod"

# Get Minikube IP
MINIKUBE_IP=$(minikube ip)

echo -e "${GREEN}=== Minikube Setup Complete ===${NC}\n"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Add the following entries to your /etc/hosts file:"
echo "   ${MINIKUBE_IP} magflow-dev.local"
echo "   ${MINIKUBE_IP} magflow-prod.local"
echo -e "\n2. Access the Kubernetes dashboard with:"
echo "   minikube dashboard"
echo -e "\n3. Access the application:"
echo "   Development: http://magflow-dev.local"
echo "   Production:  http://magflow-prod.local"
echo -e "\n4. To set up port forwarding for local development:"
echo "   kubectl port-forward -n magflow-dev svc/magflow 8000:80"
echo -e "\n5. Access the application at: http://localhost:8000\n"

echo -e "${GREEN}Your Minikube cluster is now ready for MagFlow development!${NC}\n"
