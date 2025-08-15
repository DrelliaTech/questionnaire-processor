# Drellia Audit Services Monorepo

This monorepo contains all services for the Drellia Audit system, designed to process audio files, transcribe them, parse conversations, and process questionnaires.

## Architecture Overview

```
SFTP → S3 → FileWatcher (Lambda) → AudioTranscriptionQueue (SQS)
                                        ↓
                            AudioTranscriber (Fargate)
                                        ↓
                          ConversationParserQueue (SQS)
                                        ↓
                          ConversationParser (Fargate)
                                        ↓
                              PostgreSQL + DynamoDB
                                        ↓
                          QuestionnaireProcessor (Lambda)
```

## Repository Structure

```
.
├── shared/                    # Shared packages
│   ├── models/               # Data models (Pydantic, SQLAlchemy)
│   ├── database/             # Database clients (PostgreSQL, DynamoDB)
│   └── utils/                # Utility functions (AWS clients)
│
├── services/                  # Microservices
│   ├── file-watcher/         # Lambda: S3 event handler
│   ├── audio-transcriber/    # Fargate: Audio transcription service
│   ├── conversation-parser/  # Fargate: Conversation parsing service
│   └── questionnaire-processor/ # Lambda: Questionnaire processing
│
├── aws/                       # AWS CDK Infrastructure
│   ├── infrastructure/       # CDK stack definitions
│   └── app.py               # CDK app entry point
│
├── scripts/                   # Deployment scripts
│   ├── deploy.sh            # Main deployment script
│   └── build-service.sh     # Service build script
│
└── .github/workflows/         # GitHub Actions CI/CD
```

## Service Independence

Each service is independent and has its own:
- `pyproject.toml` for dependencies
- `Dockerfile` for containerization
- GitHub Actions workflow for deployment
- Separate ECR repository

Changes to a service trigger deployment of only that service through path-based GitHub Actions triggers.

## Deployment

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. Docker installed
3. Python 3.11+
4. AWS CDK CLI (`npm install -g aws-cdk`)

### Deploy Everything

```bash
./scripts/deploy.sh DEV all
```

### Deploy Individual Services

```bash
# Deploy infrastructure only
./scripts/deploy.sh DEV infrastructure

# Deploy specific service
./scripts/deploy.sh DEV file-watcher
./scripts/deploy.sh DEV audio-transcriber
./scripts/deploy.sh DEV conversation-parser
./scripts/deploy.sh DEV questionnaire-processor
```

### Environment Variables

Services use the following environment variables:

- `ENVIRONMENT`: DEV or PROD
- `AWS_REGION`: AWS region (default: eu-north-1)
- `AUDIO_TRANSCRIPTION_QUEUE_URL`: SQS queue for audio jobs
- `CONVERSATION_PARSER_QUEUE_URL`: SQS queue for parsing jobs
- `DYNAMODB_MESSAGES_TABLE`: DynamoDB table name
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `S3_BUCKET_NAME`: S3 bucket for audio files
- `OPENAI_API_KEY`: OpenAI API key for questionnaire processing

## CI/CD

GitHub Actions workflows are configured for automatic deployment:

- **Push to `develop` branch**: Deploys to DEV environment
- **Push to `main` branch**: Deploys to PROD environment
- **Path-based triggers**: Only affected services are deployed

Each service has its own workflow that triggers only when files in its directory or shared packages change.

## Local Development

### Running Services Locally

1. Install dependencies:
```bash
cd services/[service-name]
poetry install
```

2. Set environment variables:
```bash
export ENVIRONMENT=DEV
export AWS_REGION=eu-north-1
# ... other required variables
```

3. Run the service:
```bash
poetry run python src/main.py
```

### Building Docker Images Locally

```bash
./scripts/build-service.sh [service-name]
```

## Testing

Run tests for a specific service:
```bash
cd services/[service-name]
poetry run pytest
```

Run all tests:
```bash
poetry run pytest
```

## Shared Packages

### drellia-models
Contains shared data models using Pydantic and SQLAlchemy.

### drellia-database
Database client implementations for PostgreSQL and DynamoDB.

### drellia-utils
AWS service clients and utility functions.

## Security Considerations

- All S3 buckets have encryption enabled
- VPC endpoints are used for AWS services
- Secrets are stored in AWS Secrets Manager
- IAM roles follow least privilege principle
- All traffic between services is encrypted

## Monitoring

- CloudWatch Logs for all services
- Container Insights for ECS services
- Lambda function metrics
- SQS queue metrics

## Account Structure

- **DEVOPS Account (151508346231)**: ECR repositories
- **DEV Account (505825010410)**: Development environment
- **PROD Account (469656055410)**: Production environment