#!/bin/bash
set -e

# Configuration
ENVIRONMENT=${1:-DEV}
SERVICE=${2:-all}
AWS_REGION=${AWS_REGION:-eu-north-1}

# Account mapping
declare -A ACCOUNTS
ACCOUNTS["DEVOPS"]="151508346231"
ACCOUNTS["DEV"]="505825010410"
ACCOUNTS["PROD"]="469656055410"

ECR_ACCOUNT=${ACCOUNTS["DEVOPS"]}
TARGET_ACCOUNT=${ACCOUNTS[$ENVIRONMENT]}

if [ -z "$TARGET_ACCOUNT" ]; then
    echo "Invalid environment: $ENVIRONMENT"
    exit 1
fi

echo "Deploying to $ENVIRONMENT environment (Account: $TARGET_ACCOUNT)"

# Function to build and push Docker image
build_and_push() {
    local service_name=$1
    local service_path=$2
    local repo_name="drellia-audit/${service_name}-${ENVIRONMENT,,}"
    
    echo "Building $service_name..."
    
    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $ECR_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
    
    # Build image
    docker build -t $service_name:latest $service_path
    
    # Tag image
    docker tag $service_name:latest \
        $ECR_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$repo_name:latest
    
    # Push image
    docker push $ECR_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$repo_name:latest
    
    echo "$service_name deployed successfully"
}

# Deploy infrastructure
deploy_infrastructure() {
    echo "Deploying infrastructure..."
    cd aws
    pip install -r requirements.txt
    cdk deploy DrelliaAudit-$ENVIRONMENT \
        --context environment=$ENVIRONMENT \
        --require-approval never
    cd ..
}

# Deploy specific service or all services
case $SERVICE in
    infrastructure)
        deploy_infrastructure
        ;;
    file-watcher)
        build_and_push "file-watcher" "services/file-watcher"
        ;;
    audio-transcriber)
        build_and_push "audio-transcriber" "services/audio-transcriber"
        ;;
    conversation-parser)
        build_and_push "conversation-parser" "services/conversation-parser"
        ;;
    questionnaire-processor)
        build_and_push "questionnaire-processor" "services/questionnaire-processor"
        ;;
    all)
        deploy_infrastructure
        build_and_push "file-watcher" "services/file-watcher"
        build_and_push "audio-transcriber" "services/audio-transcriber"
        build_and_push "conversation-parser" "services/conversation-parser"
        build_and_push "questionnaire-processor" "services/questionnaire-processor"
        ;;
    *)
        echo "Invalid service: $SERVICE"
        echo "Usage: $0 [ENVIRONMENT] [SERVICE]"
        echo "Services: infrastructure, file-watcher, audio-transcriber, conversation-parser, questionnaire-processor, all"
        exit 1
        ;;
esac

echo "Deployment complete!"