#!/bin/bash

# Exit on error
set -e

# Set default values
NAMESPACE=${1:-default}
ENVIRONMENT=${2:-production}

# Apply namespace if it doesn't exist
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

echo "🚀 Deploying MagFlow to namespace: $NAMESPACE (Environment: $ENVIRONMENT)"

# Apply ConfigMaps
echo "📋 Applying ConfigMaps..."
kubectl apply -f deploy/k8s/configmap.yaml -n $NAMESPACE

# Apply Secrets
echo "🔑 Applying Secrets..."
# Note: You need to create the secrets first using the secrets.yaml as a template
# kubectl apply -f deploy/k8s/secrets.yaml -n $NAMESPACE
echo "⚠️  Please ensure secrets are created before proceeding (see deploy/k8s/secrets.yaml)"

# Apply Deployment
echo "🚀 Applying Deployment..."
kubectl apply -f deploy/k8s/deployment.yaml -n $NAMESPACE

# Apply Service
echo "🔌 Applying Service..."
kubectl apply -f deploy/k8s/service.yaml -n $NAMESPACE

# Apply HPA
echo "📈 Applying Horizontal Pod Autoscaler..."
kubectl apply -f deploy/k8s/hpa.yaml -n $NAMESPACE

# Apply Ingress
echo "🌐 Applying Ingress..."
# Only apply ingress in production or if explicitly specified
if [ "$ENVIRONMENT" = "production" ] || [ "$APPLY_INGRESS" = "true" ]; then
    kubectl apply -f deploy/k8s/ingress.yaml -n $NAMESPACE
else
    echo "⚠️  Skipping Ingress in non-production environment. Set APPLY_INGRESS=true to apply."
fi

echo "✅ Deployment complete!"
echo "
📋 Next steps:
1. Check deployment status: kubectl get pods -n $NAMESPACE
2. View logs: kubectl logs -f deployment/magflow-app -n $NAMESPACE
3. Port-forward to access the API: kubectl port-forward svc/magflow-service 8000:80 -n $NAMESPACE
4. Access the API at: http://localhost:8000/api/v1/docs
"

# Show current status
echo "📊 Current status:"
kubectl get all -n $NAMESPACE
