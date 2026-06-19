# Building and Publishing Docker Container

This guide explains how to build the py-kms Docker container locally and publish it to Docker Hub.

## Prerequisites

- Docker installed and running on your system
- Docker Hub account ([signup here](https://hub.docker.com/signup))
- Git (optional, for cloning the repository)

## Step 1: Clone or Download the Repository

If you haven't already, clone the repository:

```bash
git clone https://github.com/py-kms-organization/py-kms.git
cd py-kms
```

Or download and extract the ZIP archive from GitHub.

## Step 2: Build the Docker Image

Navigate to the project root directory and build the image:

```bash
# Basic build
docker build -f docker/docker-py3-kms/Dockerfile -t your-username/py-kms:latest .

# Build with custom version info (recommended)
docker build \
  -f docker/docker-py3-kms/Dockerfile \
  --build-arg BUILD_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
  --build-arg BUILD_REFERENCE=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown") \
  -t your-username/py-kms:latest \
  .
```

**Replace `your-username` with your Docker Hub username.**

### Build Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `BUILD_COMMIT` | Git commit hash for version tracking | `unknown` |
| `BUILD_REFERENCE` | Git branch/tag name | `unknown` |

### Example with Version Tags

```bash
# Tag with version
docker build -f docker/docker-py3-kms/Dockerfile -t your-username/py-kms:1.0.0 .

# Also tag as latest
docker tag your-username/py-kms:1.0.0 your-username/py-kms:latest
```

## Step 3: Test the Image Locally

Before publishing, test the image locally:

```bash
docker run -d --name py-kms-test \
  -p 1688:1688 -p 8080:8080 \
  -e WEBUI=1 \
  your-username/py-kms:latest

# Check logs
docker logs py-kms-test

# Test KMS port (Windows)
# telnet localhost 1688

# Test WebUI
# Open http://localhost:8080 in browser

# Test metrics endpoint
curl http://localhost:8080/metrics

# Stop and remove test container
docker stop py-kms-test && docker rm py-kms-test
```

## Step 4: Login to Docker Hub

```bash
docker login
```

Enter your Docker Hub username and password (or use a personal access token for better security).

## Step 5: Push to Docker Hub

```bash
# Push latest tag
docker push your-username/py-kms:latest

# Push specific version
docker push your-username/py-kms:1.0.0
```

## Step 6: Verify the Publication

1. Go to https://hub.docker.com/r/your-username/py-kms
2. Verify that the tags appear correctly
3. Check the build date and size

## Quick Reference: Complete Build & Publish Script

```bash
#!/bin/bash
set -e

# Configuration
DOCKER_USERNAME="your-username"
IMAGE_NAME="py-kms"
VERSION="1.0.0"

# Navigate to project root
cd "$(dirname "$0")/.."

# Build the image
echo "Building Docker image..."
docker build \
  -f docker/docker-py3-kms/Dockerfile \
  --build-arg BUILD_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
  --build-arg BUILD_REFERENCE=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown") \
  -t ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION} \
  -t ${DOCKER_USERNAME}/${IMAGE_NAME}:latest \
  .

# Test locally (optional)
echo "Testing image locally..."
docker run -d --name py-kms-test \
  -p 1688:1688 -p 8080:8080 \
  -e WEBUI=1 \
  ${DOCKER_USERNAME}/${IMAGE_NAME}:latest

sleep 5
docker logs py-kms-test
docker stop py-kms-test && docker rm py-kms-test

# Login to Docker Hub
echo "Logging in to Docker Hub..."
docker login

# Push to Docker Hub
echo "Pushing to Docker Hub..."
docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION}
docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:latest

echo "Done! Image available at: https://hub.docker.com/r/${DOCKER_USERNAME}/${IMAGE_NAME}"
```

## Usage After Publishing

Once published, users can run your image with:

```bash
docker run -d --name py-kms --restart always \
  -p 1688:1688 -p 8080:8080 \
  -e WEBUI=1 \
  your-username/py-kms:latest
```

## Docker Compose Example

Create a `docker-compose.yml` for easier deployment:

```yaml
version: '3.8'
services:
  py-kms:
    image: your-username/py-kms:latest
    container_name: py-kms
    ports:
      - "1688:1688"
      - "8080:8080"
    environment:
      - WEBUI=1
      - TZ=UTC
    volumes:
      - py-kms-data:/home/py-kms/db
    restart: always

volumes:
  py-kms-data:
```

## Troubleshooting

### Build fails with "permission denied"
Run Docker with appropriate permissions or add your user to the `docker` group (Linux).

### Image is too large
Consider using the `docker-py3-kms-minimal` variant instead:
```bash
docker build -f docker/docker-py3-kms-minimal/Dockerfile -t your-username/py-kms:latest .
```

### Push fails with "unauthorized"
Run `docker login` again and verify your credentials.

### Multi-architecture builds (Advanced)

To build for multiple architectures (amd64, arm64):

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Create/buildx builder
docker buildx create --name mybuilder --use

# Build and push multi-arch image
docker buildx build \
  -f docker/docker-py3-kms/Dockerfile \
  --platform linux/amd64,linux/arm64 \
  --build-arg BUILD_COMMIT=$(git rev-parse --short HEAD) \
  --build-arg BUILD_REFERENCE=$(git rev-parse --abbrev-ref HEAD) \
  -t your-username/py-kms:latest \
  --push \
  .
```

## Security Best Practices

1. **Use specific version tags** in production, not `:latest`
2. **Enable read-only root filesystem** where possible
3. **Scan images for vulnerabilities** before publishing:
   ```bash
   docker scan your-username/py-kms:latest
   ```
4. **Use Docker Hub private repositories** for internal builds
5. **Rotate credentials** regularly and use access tokens instead of passwords
