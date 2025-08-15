#!/bin/bash
set -e

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "Usage: $0 <service-name>"
    echo "Services: file-watcher, audio-transcriber, conversation-parser, questionnaire-processor"
    exit 1
fi

SERVICE_PATH="services/$SERVICE"

if [ ! -d "$SERVICE_PATH" ]; then
    echo "Service directory not found: $SERVICE_PATH"
    exit 1
fi

echo "Building $SERVICE..."

# Copy shared packages to service directory temporarily
cp -r shared $SERVICE_PATH/

# Build Docker image
docker build -t $SERVICE:latest $SERVICE_PATH

# Clean up copied shared packages
rm -rf $SERVICE_PATH/shared

echo "$SERVICE built successfully"