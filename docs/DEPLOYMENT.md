# MagFlow ERP - Deployment Guide

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-blue.svg)](https://kubernetes.io/)
[![AWS](https://img.shields.io/badge/AWS-Ready-orange.svg)](https://aws.amazon.com/)

Comprehensive deployment guide for MagFlow ERP across different environments and platforms.

## 📋 Table of Contents

- [Deployment Overview](#deployment-overview)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Platform Deployment](#cloud-platform-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Monitoring & Observability](#monitoring--observability)
- [Backup & Recovery](#backup--recovery)
- [Security Considerations](#security-considerations)
- [Performance Optimization](#performance-optimization)

## 🚀 Deployment Overview

### Deployment Environments

#### Development Environment
- **Purpose**: Local development and testing
- **URL**: http://localhost:8000
- **Database**: Local PostgreSQL
- **Features**: Hot reload, debug logging
- **Security**: Minimal security (dev only)

#### Staging Environment
- **Purpose**: Pre-production testing
- **URL**: https://staging.magflow-erp.com
- **Database**: Separate staging database
- **Features**: Production-like configuration
- **Security**: Full security except production keys

#### Production Environment
- **Purpose**: Live production system
- **URL**: https://magflow-erp.com
- **Database**: Production PostgreSQL cluster
- **Features**: Optimized for performance
- **Security**: Full production security

### Deployment Strategies

#### Blue-Green Deployment
```bash
# 1. Deploy to blue environment
kubectl apply -f deployment/kubernetes/blue/

# 2. Test blue environment
curl https://blue.magflow-erp.com/health

# 3. Switch traffic to blue
kubectl apply -f deployment/kubernetes/green-to-blue/

# 4. Remove green environment
kubectl delete -f deployment/kubernetes/green/
```

#### Rolling Deployment
```bash
# Update deployment with rolling update strategy
kubectl set image deployment/magflow-erp app=magflow-erp:v2.0.0

# Monitor rollout
kubectl rollout status deployment/magflow-erp

# Rollback if needed
kubectl rollout undo deployment/magflow-erp
```

#### Canary Deployment
```bash
# Deploy canary version
kubectl apply -f deployment/kubernetes/canary/

# Route 10% traffic to canary
kubectl apply -f deployment/kubernetes/canary-traffic/

# Monitor canary metrics
kubectl logs -f deployment/magflow-erp-canary

# Promote canary to production
kubectl apply -f deployment/kubernetes/promote-canary/
```

## ⚙️ Environment Setup

### Configuration Files

#### Environment Variables
```bash
# .env.production
# Database
POSTGRES_SERVER=prod-postgres.magflow-erp.com
POSTGRES_USER=magflow_prod
POSTGRES_PASSWORD=secure_prod_password
POSTGRES_DB=magflow_prod
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://magflow_prod:secure_prod_password@prod-postGRES.magflow-erp.com/magflow_prod

# Security
SECRET_KEY=your-production-secret-key-here-min-256-bits
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# Application
APP_ENV=production
DEBUG=False
API_V1_STR=/api/v1

# External APIs
EMAG_API_URL=https://api.emag.ro
EMAG_API_USERNAME=prod_username
EMAG_API_PASSWORD=prod_password

# Redis
REDIS_HOST=prod-redis.magflow-erp.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=secure_redis_password

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
LOG_LEVEL=WARNING
```

#### Docker Configuration
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: magflow-erp:production
    environment:
      - POSTGRES_SERVER=postgres
      - REDIS_HOST=redis
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: magflow_prod
      POSTGRES_USER: magflow_prod
      POSTGRES_PASSWORD: secure_prod_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U magflow_prod -d magflow_prod"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass secure_redis_password
    volumes:
      - redis_data:/data
```

#### Kubernetes Configuration
```yaml
# deployment/kubernetes/production.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: magflow-erp-production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: magflow-erp
      environment: production
  template:
    metadata:
      labels:
        app: magflow-erp
        environment: production
    spec:
      containers:
      - name: magflow-erp
        image: magflow-erp:production
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_SERVER
          valueFrom:
            secretKeyRef:
              name: magflow-secrets
              key: postgres-server
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## 🐳 Docker Deployment

### Development Docker Setup

#### 1. Build Development Image
```bash
# Build development image
docker build -t magflow-erp:dev .

# Or build with specific target
docker build -t magflow-erp:dev --target development .
```

#### 2. Run Development Environment
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Access application
curl http://localhost:8000/health
```

#### 3. Development Workflow with Docker
```bash
# Make code changes
vim app/main.py

# Restart application
docker-compose restart app

# View application logs
docker-compose logs -f app

# Execute commands in container
docker-compose exec app python -c "print('Hello from container')"

# Run tests in container
docker-compose exec app pytest tests/
```

### Production Docker Setup

#### 1. Multi-Stage Docker Build
```dockerfile
# Dockerfile.production
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash magflow
USER magflow
WORKDIR /home/magflow

FROM base AS dependencies

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM base AS production

# Copy installed packages from dependencies stage
COPY --from=dependencies /home/magflow/.local /home/magflow/.local

# Copy application code
COPY --chown=magflow:magflow app/ ./app/

# Create non-root user and set permissions
RUN mkdir -p logs certs && chown -R magflow:magflow logs certs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Production Docker Compose
```yaml
# docker-compose.production.yml
version: '3.8'

services:
  app:
    image: magflow-erp:production
    environment:
      - POSTGRES_SERVER=postgres
      - REDIS_HOST=redis
      - APP_ENV=production
      - DEBUG=False
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: magflow_prod
      POSTGRES_USER: magflow_prod
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U magflow_prod -d magflow_prod"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      placement:
        constraints: [node.role == manager]

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    deploy:
      restart_policy:
        condition: on-failure
```

#### 3. Docker Swarm Deployment
```bash
# Initialize Docker Swarm
docker swarm init

# Deploy application stack
docker stack deploy -c docker-compose.production.yml magflow-erp

# Check services
docker stack services magflow-erp

# Scale application
docker service scale magflow-erp_app=5

# View logs
docker service logs magflow-erp_app -f

# Update application
docker service update --image magflow-erp:production magflow-erp_app
```

## ☸️ Kubernetes Deployment

### Kubernetes Architecture

#### Namespace Setup
```bash
# Create namespace
kubectl create namespace magflow-erp

# Set context
kubectl config set-context --current --namespace=magflow-erp
```

#### ConfigMap for Application Configuration
```yaml
# deployment/kubernetes/configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: magflow-config
data:
  APP_ENV: "production"
  DEBUG: "False"
  LOG_LEVEL: "INFO"
  API_V1_STR: "/api/v1"
```

#### Secrets for Sensitive Data
```yaml
# deployment/kubernetes/secrets.yml
apiVersion: v1
kind: Secret
metadata:
  name: magflow-secrets
type: Opaque
data:
  postgres-server: <base64-encoded-db-server>
  postgres-user: <base64-encoded-db-user>
  postgres-password: <base64-encoded-db-password>
  redis-password: <base64-encoded-redis-password>
  secret-key: <base64-encoded-secret-key>
```

#### Deployment with Health Checks
```yaml
# deployment/kubernetes/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: magflow-erp
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: magflow-erp
  template:
    metadata:
      labels:
        app: magflow-erp
    spec:
      containers:
      - name: magflow-erp
        image: magflow-erp:production
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: magflow-config
        - secretRef:
            name: magflow-secrets
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        emptyDir: {}
```

#### Service Configuration
```yaml
# deployment/kubernetes/service.yml
apiVersion: v1
kind: Service
metadata:
  name: magflow-erp
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: magflow-erp

---
apiVersion: v1
kind: Service
metadata:
  name: magflow-erp-loadbalancer
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: magflow-erp
```

#### Ingress Configuration
```yaml
# deployment/kubernetes/ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: magflow-erp
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - magflow-erp.com
    secretName: magflow-erp-tls
  rules:
  - host: magflow-erp.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: magflow-erp
            port:
              number: 80
```

### Kubernetes Operations

#### Deploy to Kubernetes
```bash
# Apply all configurations
kubectl apply -f deployment/kubernetes/

# Check deployment status
kubectl get pods
kubectl get services
kubectl get ingress

# View logs
kubectl logs -f deployment/magflow-erp

# Scale application
kubectl scale deployment magflow-erp --replicas=5

# Update application
kubectl set image deployment/magflow-erp magflow-erp=magflow-erp:production
```

#### Monitoring Kubernetes
```bash
# Check resource usage
kubectl top pods
kubectl top nodes

# Describe deployment
kubectl describe deployment magflow-erp

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Debug pods
kubectl describe pod magflow-erp-xxxxx-yyyyy
kubectl logs magflow-erp-xxxxx-yyyyy --previous
```

#### Backup and Recovery
```bash
# Backup etcd
kubectl get all -o yaml > cluster-backup.yaml

# Backup persistent volumes
kubectl get pvc -o yaml > pvc-backup.yaml

# Backup database
kubectl exec postgres-pod -- pg_dumpall -U magflow > db-backup.sql
```

## ☁️ Cloud Platform Deployment

### AWS Deployment

#### 1. RDS PostgreSQL Setup
```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier magflow-prod \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.0 \
  --master-username magflow \
  --master-user-password secure_password \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name magflow-subnet-group

# Create ElastiCache Redis
aws elasticache create-cluster \
  --cluster-id magflow-redis \
  --engine redis \
  --engine-version 7.0 \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1
```

#### 2. ECS Fargate Deployment
```yaml
# deployment/aws/ecs-task-definition.json
{
  "family": "magflow-erp",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/magflow-task-role",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/magflow-execution-role",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "magflow-erp",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/magflow-erp:production",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "POSTGRES_SERVER",
          "value": "magflow-prod.xxxxx.us-east-1.rds.amazonaws.com"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:magflow/db"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/magflow-erp",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 3. Application Load Balancer
```bash
# Create target group
aws elbv2 create-target-group \
  --name magflow-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxx \
  --target-type ip

# Create load balancer
aws elbv2 create-load-balancer \
  --name magflow-alb \
  --subnets subnet-1 subnet-2 \
  --security-groups sg-xxxxx

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:loadbalancer/app/magflow-alb/xxxx \
  --protocol HTTPS \
  --port 443 \
  --ssl-policy ELBSecurityPolicy-TLS-1-2-2017-01 \
  --certificate-arn arn:aws:acm:us-east-1:ACCOUNT:certificate/xxxx \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/magflow-targets/xxxx
```

### Azure Deployment

#### 1. Azure Database for PostgreSQL
```bash
# Create PostgreSQL server
az postgres server create \
  --resource-group magflow-rg \
  --name magflow-postgres \
  --location eastus \
  --admin-user magflow \
  --admin-password secure_password \
  --sku-name B_Gen5_1

# Create database
az postgres db create \
  --resource-group magflow-rg \
  --server-name magflow-postgres \
  --name magflow_prod
```

#### 2. Azure Container Instances
```yaml
# deployment/azure/container-instances.yml
apiVersion: 2019-12-01
type: Microsoft.ContainerInstance/containerGroups
name: magflow-erp
location: eastus
properties:
  containers:
  - name: magflow-erp
    properties:
      image: magflow-erp:production
      ports:
      - port: 8000
      environmentVariables:
      - name: POSTGRES_SERVER
        value: magflow-postgres.postgres.database.azure.com
      - name: APP_ENV
        value: production
      resources:
        requests:
          cpu: 1
          memoryInGb: 1.5
  osType: Linux
  ipAddress:
    type: Public
    ports:
    - port: 8000
```

#### 3. Azure Kubernetes Service
```bash
# Create AKS cluster
az aks create \
  --resource-group magflow-rg \
  --name magflow-aks \
  --node-count 3 \
  --node-vm-size Standard_B2s \
  --enable-managed-identity \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group magflow-rg --name magflow-aks

# Deploy application
kubectl apply -f deployment/kubernetes/
```

### Google Cloud Deployment

#### 1. Cloud SQL PostgreSQL
```bash
# Create Cloud SQL instance
gcloud sql instances create magflow-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=secure_password

# Create database
gcloud sql databases create magflow_prod --instance=magflow-postgres
```

#### 2. Cloud Run Deployment
```yaml
# deployment/gcp/cloud-run.yml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: magflow-erp
spec:
  template:
    spec:
      containers:
      - image: gcr.io/PROJECT/magflow-erp:production
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_SERVER
          value: "/cloudsql/PROJECT:us-central1:magflow-postgres"
        - name: APP_ENV
          value: "production"
      serviceAccountName: magflow-service-account
```

#### 3. Google Kubernetes Engine
```bash
# Create GKE cluster
gcloud container clusters create magflow-gke \
  --num-nodes=3 \
  --zone=us-central1-a \
  --machine-type=n1-standard-1

# Get credentials
gcloud container clusters get-credentials magflow-gke --zone=us-central1-a

# Deploy application
kubectl apply -f deployment/kubernetes/
```

## 🚀 CI/CD Pipeline

### GitHub Actions CI/CD

#### 1. CI Pipeline
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    - name: Run tests
      run: pytest tests/ --cov=app --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

#### 2. CD Pipeline
```yaml
# .github/workflows/cd.yml
name: CD

on:
  push:
    tags: [ 'v*' ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: magflow-erp:${{ github.ref_name }},magflow-erp:latest
    - name: Deploy to Kubernetes
      uses: azure/k8s-deploy@v4
      with:
        manifests: deployment/kubernetes/
        namespace: magflow-erp
```

#### 3. Security Scanning
```yaml
# .github/workflows/security.yml
name: Security

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
```

### GitLab CI/CD

#### 1. Complete GitLab Pipeline
```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy-staging
  - deploy-production

variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE/magflow-erp
  POSTGRES_DB: magflow_test
  POSTGRES_USER: magflow
  POSTGRES_PASSWORD: test_password

test:
  stage: test
  image: python:3.11
  services:
    - postgres:15
    - redis:7
  script:
    - pip install -r requirements-dev.txt
    - pytest tests/ --cov=app --cov-report=xml
    - black --check app/
    - ruff check app/
    - mypy app/
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

build:
  stage: build
  image: docker:20
  services:
    - docker:20-dind
  script:
    - docker build -t $DOCKER_IMAGE:$CI_COMMIT_SHA .
    - docker push $DOCKER_IMAGE:$CI_COMMIT_SHA
  only:
    - main
    - tags

deploy-staging:
  stage: deploy-staging
  image: alpine/k8s:1.25
  script:
    - kubectl apply -f deployment/kubernetes/staging/
    - kubectl set image deployment/magflow-erp app=$DOCKER_IMAGE:$CI_COMMIT_SHA
    - kubectl rollout status deployment/magflow-erp
  environment:
    name: staging
  only:
    - main

deploy-production:
  stage: deploy-production
  image: alpine/k8s:1.25
  script:
    - kubectl apply -f deployment/kubernetes/production/
    - kubectl set image deployment/magflow-erp app=$DOCKER_IMAGE:$CI_COMMIT_SHA
    - kubectl rollout status deployment/magflow-erp
  environment:
    name: production
  only:
    - tags
  when: manual
```

## 📊 Monitoring & Observability

### Application Monitoring

#### Health Checks
```yaml
# deployment/kubernetes/health-checks.yml
apiVersion: v1
kind: Service
metadata:
  name: magflow-health
spec:
  selector:
    app: magflow-erp
  ports:
  - port: 80
    targetPort: 8000
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: magflow-erp
spec:
  selector:
    matchLabels:
      app: magflow-erp
  endpoints:
  - port: web
    path: /metrics
    interval: 30s
```

#### Prometheus Configuration
```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
- job_name: 'magflow-erp'
  static_configs:
  - targets: ['magflow-erp:8000']
  metrics_path: /metrics

- job_name: 'postgres'
  static_configs:
  - targets: ['postgres-exporter:9187']

- job_name: 'redis'
  static_configs:
  - targets: ['redis-exporter:9121']
```

#### Grafana Dashboards
```yaml
# monitoring/grafana/dashboards/magflow-overview.json
{
  "dashboard": {
    "title": "MagFlow ERP Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "stat",
        "targets": [
          {
            "expr": "pg_stat_activity_count"
          }
        ]
      }
    ]
  }
}
```

### Log Management

#### Fluentd Configuration
```yaml
# deployment/logging/fluentd-configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*magflow*.log
      tag magflow
      format json
    </source>

    <filter magflow>
      @type record_transformer
      <record>
        service magflow-erp
      </record>
    </filter>

    <match magflow>
      @type elasticsearch
      host elasticsearch
      port 9200
      index_name magflow-logs
    </match>
```

#### Elasticsearch Setup
```yaml
# deployment/logging/elasticsearch.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
        env:
        - name: discovery.type
          value: single-node
        volumeMounts:
        - name: data
          mountPath: /usr/share/elasticsearch/data
      volumes:
      - name: data
        emptyDir: {}
```

#### Kibana Setup
```yaml
# deployment/logging/kibana.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kibana
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: kibana
        image: docker.elastic.co/kibana/kibana:8.5.0
        env:
        - name: ELASTICSEARCH_HOSTS
          value: http://elasticsearch:9200
        ports:
        - containerPort: 5601
```

## 💾 Backup & Recovery

### Database Backup

#### PostgreSQL Backup
```bash
# Create database backup
pg_dump magflow_prod > magflow_prod_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
pg_dump magflow_prod | gzip > magflow_prod_$(date +%Y%m%d_%H%M%S).sql.gz

# Automated backup script
#!/bin/bash
# backup-db.sh
BACKUP_DIR="/var/backups/magflow"
mkdir -p $BACKUP_DIR

# Create backup
pg_dump magflow_prod | gzip > $BACKUP_DIR/magflow_prod_$(date +%Y%m%d_%H%M%S).sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

#### Kubernetes Database Backup
```yaml
# deployment/backup/cronjob.yml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: magflow-db-backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            command: ["/bin/bash", "-c"]
            args:
            - |
              pg_dump magflow_prod | gzip > /backup/magflow_prod_$(date +%Y%m%d_%H%M%S).sql.gz &&
              aws s3 cp /backup/magflow_prod_$(date +%Y%m%d_%H%M%S).sql.gz s3://magflow-backups/
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### File System Backup

#### Docker Volumes Backup
```bash
# Backup Docker volumes
docker run --rm -v magflow_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz /data

# Restore Docker volumes
docker run --rm -v magflow_postgres_data:/data -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/postgres_data.tar.gz"
```

#### Kubernetes Persistent Volumes Backup
```yaml
# deployment/backup/pvc-backup.yml
apiVersion: v1
kind: Pod
metadata:
  name: pvc-backup
spec:
  containers:
  - name: backup
    image: alpine
    command: ["/bin/sh"]
    args:
    - -c
    - |
      tar czf /backup/magflow-data-$(date +%Y%m%d-%H%M%S).tar.gz /data &&
      aws s3 cp /backup/magflow-data-$(date +%Y%m%d-%H%M%S).tar.gz s3://magflow-backups/
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: magflow-data-pvc
```

### Recovery Procedures

#### Database Recovery
```bash
# Drop existing database
dropdb magflow_prod

# Create fresh database
createdb magflow_prod

# Restore from backup
gunzip -c magflow_prod_20240101_020000.sql.gz | psql magflow_prod

# Verify restore
psql magflow_prod -c "SELECT COUNT(*) FROM users;"
```

#### Kubernetes Recovery
```bash
# Scale down application
kubectl scale deployment magflow-erp --replicas=0

# Restore database from backup
kubectl apply -f deployment/backup/postgres-restore.yml

# Scale up application
kubectl scale deployment magflow-erp --replicas=3

# Verify recovery
kubectl get pods
kubectl logs -f deployment/magflow-erp
```

## 🔒 Security Considerations

### Production Security Checklist

#### Authentication & Authorization
- [ ] JWT tokens with appropriate expiration
- [ ] Secure password hashing (bcrypt)
- [ ] Role-based access control (RBAC)
- [ ] API rate limiting
- [ ] Input validation and sanitization

#### Network Security
- [ ] HTTPS only in production
- [ ] Firewall rules configured
- [ ] Private subnets for databases
- [ ] Security groups properly configured
- [ ] DDoS protection enabled

#### Data Security
- [ ] Database encryption at rest
- [ ] SSL/TLS for database connections
- [ ] Regular security updates
- [ ] Vulnerability scanning
- [ ] Secure key management

#### Application Security
- [ ] Dependency vulnerability scanning
- [ ] Container security scanning
- [ ] Security headers configured
- [ ] CORS properly configured
- [ ] SQL injection prevention

### Security Monitoring
```yaml
# monitoring/alerts/security-alerts.yml
groups:
- name: security_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is above 10% for the last 5 minutes"

  - alert: UnauthorizedAccess
    expr: rate(http_requests_total{status="401"}[5m]) > 10
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High unauthorized access rate"
      description: "More than 10 unauthorized requests per 5 minutes"
```

### Compliance & Audit
```yaml
# app/core/audit.py
import logging
from typing import Dict, Any
from fastapi import Request

async def log_security_event(
    event_type: str,
    user_id: int,
    details: Dict[str, Any],
    request: Request
):
    """Log security events for audit purposes."""
    log_entry = {
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": datetime.utcnow(),
        **details
    }

    logger = logging.getLogger("security_audit")
    logger.info(f"Security event: {log_entry}")

# Usage in API endpoints
@router.post("/admin/users")
async def admin_create_user(
    user_data: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_admin_user)
):
    # Log security event
    await log_security_event(
        "admin_user_created",
        current_user.id,
        {"target_user_email": user_data.email},
        request
    )

    # Create user
    user = await user_crud.create_user(db, user_data)
    return user
```

## ⚡ Performance Optimization

### Database Performance

#### Connection Pooling
```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    # Connection pool settings
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    # Performance settings
    echo=settings.DEBUG,
    future=True
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

#### Query Optimization
```python
# app/crud/base.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, TypeVar, Type, Generic

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        # Use select() instead of deprecated query()
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_multi_with_relations(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        # Eager load relationships
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.related_objects))
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
```

### Caching Strategy

#### Redis Cache Implementation
```python
# app/services/cache_service.py
from typing import Optional, Any
import json
import redis.asyncio as redis
from app.core.config import settings

class CacheService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    async def get_cached_data(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set_cached_data(
        self,
        key: str,
        value: Any,
        expire: int = 3600
    ):
        await self.redis.setex(
            key,
            expire,
            json.dumps(value, default=str)
        )

    async def delete_cached_data(self, key: str):
        await self.redis.delete(key)

    async def clear_cache_pattern(self, pattern: str):
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

# Usage in service layer
cache_service = CacheService()

async def get_user_with_cache(user_id: int):
    cache_key = f"user:{user_id}"

    # Try cache first
    cached_user = await cache_service.get_cached_data(cache_key)
    if cached_user:
        return json.loads(cached_user)

    # Fetch from database
    user = await user_crud.get(db, id=user_id)

    # Cache for 1 hour
    await cache_service.set_cached_data(
        cache_key, user, 3600
    )

    return user
```

### Application Performance

#### FastAPI Optimization
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

app = FastAPI(
    title="MagFlow ERP",
    version="1.0.0",
    description="Enterprise Resource Planning System",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add performance middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/health/detailed")
async def detailed_health_check():
    return {
        "status": "healthy",
        "database": check_database_health(),
        "redis": check_redis_health(),
        "external_apis": check_external_apis_health()
    }
```

#### Background Tasks
```python
# app/services/background_tasks.py
from fastapi import BackgroundTasks
import asyncio
from typing import List

async def send_email_notification(email_data: dict):
    """Send email notification in background."""
    await asyncio.sleep(0.1)  # Simulate email sending
    print(f"Email sent to {email_data['email']}")

async def process_order_notification(order_id: int):
    """Process order notification."""
    # Get order details
    order = await order_crud.get(db, id=order_id)

    # Send notifications
    await send_email_notification({
        "email": order.customer_email,
        "subject": "Order Confirmation",
        "body": f"Your order {order.order_number} has been processed."
    })

    # Update order status
    await order_crud.update_status(db, order_id, "notified")

# Usage in API
@router.post("/orders/{order_id}/process")
async def process_order(
    order_id: int,
    background_tasks: BackgroundTasks
):
    # Add background task
    background_tasks.add_task(process_order_notification, order_id)

    return {"message": "Order processing started"}
```

#### Async Optimization
```python
# app/services/bulk_operations.py
from typing import List
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

async def bulk_create_users(
    db: AsyncSession,
    user_data_list: List[dict]
) -> List[User]:
    """Create multiple users efficiently."""
    # Use asyncio.gather for concurrent operations
    tasks = [
        user_crud.create_user(db, user_data)
        for user_data in user_data_list
    ]

    # Execute concurrently
    users = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions
    successful_users = [
        user for user in users
        if not isinstance(user, Exception)
    ]

    return successful_users

async def bulk_update_inventory(
    db: AsyncSession,
    updates: List[dict]
) -> int:
    """Bulk update inventory items."""
    # Process in chunks to avoid memory issues
    chunk_size = 100
    total_updated = 0

    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i + chunk_size]

        # Use database transactions
        async with db.begin():
            tasks = [
                inventory_crud.update_item(db, item_id, update_data)
                for item_id, update_data in chunk
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_updated += len([r for r in results if not isinstance(r, Exception)])

    return total_updated
```

---

**MagFlow ERP Deployment Guide** - Complete Deployment Documentation 🚀
