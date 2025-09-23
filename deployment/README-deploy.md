# MagFlow Kubernetes Deployment

This directory contains Kubernetes manifests and deployment scripts for the MagFlow application.

## Prerequisites

- Kubernetes cluster (v1.20+)
- `kubectl` configured to access your cluster
- `kustomize` (v4.5.0+)
- Docker (for building images)
- PostgreSQL (or compatible database)
- Redis

## Directory Structure

```
deploy/
├── k8s/                    # Kubernetes manifests
│   ├── configmap.yaml      # Application configuration
│   ├── deployment.yaml     # Application deployment
│   ├── hpa.yaml            # Horizontal Pod Autoscaler
│   ├── ingress.yaml        # Ingress configuration
│   ├── kustomization.yaml  # Kustomize configuration
│   ├── secrets.yaml        # Sensitive configuration (templates)
│   ├── service.yaml        # Kubernetes service
│   └── patches/            # Environment-specific patches
│       ├── dev-patch.yaml  # Development environment overrides
│       └── prod-patch.yaml # Production environment overrides
└── scripts/                # Deployment scripts
    └── build-and-push.sh   # Docker image build and push script
```

## Quick Start

### 1. Build and Push Docker Image

```bash
# Build the production image
./scripts/build-and-push.sh --target production --push --registry your-registry.example.com

# Or for development
./scripts/build-and-push.sh --target development --push --registry your-registry.example.com
```

### 2. Deploy to Kubernetes

#### Development

```bash
kubectl create namespace magflow-dev
kubectl apply -k k8s/overlays/development
```

#### Production

```bash
kubectl create namespace magflow-prod
kubectl apply -k k8s/overlays/production
```

## Configuration

### Environment Variables

Edit the `configmap.yaml` file to configure application settings:

```yaml
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  # ... other settings
```

### Secrets

Create a `secrets.yaml` file with your sensitive data (do not commit this file):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: magflow-secrets
type: Opaque
data:
  # Generate with: echo -n "value" | base64
  database-url: ""
  secret-key: ""
  smtp-username: ""
  smtp-password: ""
```

## Scaling

The application includes a Horizontal Pod Autoscaler (HPA) that automatically scales the number of pods based on CPU and memory usage.

### Manual Scaling

```bash
# Scale the deployment manually
kubectl scale deployment magflow-app --replicas=5 -n magflow-prod
```

### Auto-scaling

Auto-scaling is configured in `hpa.yaml` with the following defaults:
- Minimum replicas: 2
- Maximum replicas: 10
- Target CPU utilization: 70%
- Target memory utilization: 80%

## Monitoring

The application exposes Prometheus metrics on port 8010 at `/metrics`.

### Port Forwarding

```bash
# Access the application
kubectl port-forward svc/magflow-service 8000:80 -n magflow-prod

# Access metrics
kubectl port-forward svc/magflow-service 8010:8010 -n magflow-prod
```

## Upgrading

1. Build and push a new Docker image with an updated tag
2. Update the image tag in `kustomization.yaml` or via a kustomize patch
3. Apply the changes:

```bash
kubectl apply -k k8s/overlays/production
```

## Rollback

To rollback to a previous deployment:

```bash
# List revisions
kubectl rollout history deployment/magflow-app -n magflow-prod

# Rollback to previous version
kubectl rollout undo deployment/magflow-app -n magflow-prod

# Rollback to specific revision
kubectl rollout undo deployment/magflow-app --to-revision=2 -n magflow-prod
```

## Troubleshooting

### View Pod Logs

```bash
# Get pod name
kubectl get pods -n magflow-prod

# View logs
kubectl logs -f <pod-name> -n magflow-prod
```

### Debugging

```bash
# Describe pod
kubectl describe pod <pod-name> -n magflow-prod

# Execute shell in container
kubectl exec -it <pod-name> -n magflow-prod -- /bin/bash

# View events
kubectl get events -n magflow-prod --sort-by='.metadata.creationTimestamp'
```

## Cleanup

To delete all resources:

```bash
# Delete all resources in the namespace
kubectl delete all --all -n magflow-prod

# Delete the namespace
kubectl delete namespace magflow-prod
```

## License

[Your License Here]
