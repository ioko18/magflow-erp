#!/bin/bash

# Exit on error
set -e

# Default values
DOCKER_REGISTRY="your-registry.example.com"
IMAGE_NAME="magflow"
TAG="latest"
TARGET="production"
PUSH="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -r|--registry)
      DOCKER_REGISTRY="$2"
      shift # past argument
      shift # past value
      ;;
    -i|--image)
      IMAGE_NAME="$2"
      shift # past argument
      shift # past value
      ;;
    -t|--tag)
      TAG="$2"
      shift # past argument
      shift # past value
      ;;
    --target)
      TARGET="$2"
      shift # past argument
      shift # past value
      ;;
    --push)
      PUSH="true"
      shift # past argument
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Build the Docker image
echo "🚀 Building Docker image: ${IMAGE_NAME}:${TAG} (target: ${TARGET})"
docker build \
  --target ${TARGET} \
  -t ${IMAGE_NAME}:${TAG} \
  -t ${IMAGE_NAME}:latest \
  .

# Tag and push the image if requested
if [ "${PUSH}" = "true" ]; then
  if [ -n "${DOCKER_REGISTRY}" ]; then
    FULL_IMAGE_NAME="${DOCKER_REGISTRY}/${IMAGE_NAME}:${TAG}"
    echo "🏷️  Tagging image as ${FULL_IMAGE_NAME}"
    docker tag ${IMAGE_NAME}:${TAG} ${FULL_IMAGE_NAME}
    
    echo "📤 Pushing image to ${DOCKER_REGISTRY}"
    docker push ${FULL_IMAGE_NAME}
    
    # Also push as latest if it's the default tag
    if [ "${TAG}" = "latest" ]; then
      docker tag ${IMAGE_NAME}:${TAG} ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
      docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
    fi
  else
    echo "❌ Error: Docker registry not specified. Use --registry to specify a registry."
    exit 1
  fi
fi

echo "✅ Build completed successfully!"

# Show the built image
echo "\n📦 Docker image info:"
docker images | grep ${IMAGE_NAME}
