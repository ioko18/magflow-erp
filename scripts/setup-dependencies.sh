#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Setting up MagFlow Dependencies in Minikube ===${NC}\n"

# Function to check if a Kubernetes resource exists
resource_exists() {
    kubectl get "$1" -n "$2" "$3" &> /dev/null
    return $?
}

# Create namespaces if they don't exist
for ns in magflow-dev magflow-prod; do
    if ! kubectl get namespace "$ns" &> /dev/null; then
        echo -e "${YELLOW}Creating namespace: ${ns}${NC}"
        kubectl create namespace "$ns"
        kubectl label namespace "$ns" "app.kubernetes.io/name"="magflow"
        echo -e "${GREEN}✓ Created namespace: ${ns}${NC}\n"
    else
        echo -e "${GREEN}✓ Namespace ${ns} already exists${NC}\n"
    fi
done

# Deploy PostgreSQL
if ! resource_exists deployment default postgres; then
    echo -e "${YELLOW}Deploying PostgreSQL...${NC}"
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  labels:
    app: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          value: postgres
        - name: POSTGRES_DB
          value: magflow
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  labels:
    app: postgres
spec:
  ports:
  - port: 5432
    targetPort: 5432
  selector:
    app: postgres
  type: ClusterIP
EOF
    echo -e "${GREEN}✓ PostgreSQL deployed${NC}\n"
else
    echo -e "${GREEN}✓ PostgreSQL is already deployed${NC}\n"
fi

# Deploy Redis
if ! resource_exists deployment default redis; then
    echo -e "${YELLOW}Deploying Redis...${NC}"
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  labels:
    app: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
          limits:
            cpu: 200m
            memory: 200Mi
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  labels:
    app: redis
spec:
  ports:
  - port: 6379
    targetPort: 6379
  selector:
    app: redis
  type: ClusterIP
EOF
    echo -e "${GREEN}✓ Redis deployed${NC}\n"
else
    echo -e "${GREEN}✓ Redis is already deployed${NC}\n"
fi

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/postgres
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

kubectl wait --for=condition=available --timeout=300s deployment/redis
echo -e "${GREEN}✓ Redis is ready${NC}"

# Create database if it doesn't exist
echo -e "\n${YELLOW}Creating database if it doesn't exist...${NC}"
kubectl run postgres-client --rm --tty -i --restart='Never' \
  --image=postgres:15-alpine \
  --env="PGPASSWORD=postgres" \
  --command -- psql -h postgres -U postgres -d postgres -c "CREATE DATABASE magflow;" || \
  echo -e "${YELLOW}Database already exists or could not be created${NC}"

echo -e "\n${GREEN}=== Dependencies Setup Complete ===${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Run the application with: ./scripts/deploy-to-minikube.sh"
echo "2. Access the application at: http://localhost:8000"
echo -e "\n${GREEN}Your Minikube environment is now ready for MagFlow development!${NC}\n"
