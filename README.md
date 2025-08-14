# Questionnaire Processor

A comprehensive AWS Lambda-based system for processing audio communications into structured questionnaire responses. The system handles the complete pipeline from audio ingestion to questionnaire analysis.

## Architecture Overview

The system consists of multiple AWS Lambda functions working together:

```
UContact → AudioImporter → S3 → FileWatcher → AudioTranscriptionQueue → AudioTranscriber
                                                                              ↓
                                   DynamoDB ← ConversationParser ← ConversationParserQueue
                                      ↑
                              QuestionnaireProcessor ← PostgreSQL
```

### Components

- **AudioImporter**: Downloads daily communications from UContact and stores them in S3
- **FileWatcher**: Monitors S3 for new audio files and queues them for transcription
- **AudioTranscriber**: Transcribes audio files using AWS Transcribe
- **ConversationParser**: Converts transcriptions into structured conversations
- **QuestionnaireProcessor**: Analyzes conversations against predefined questionnaires

### Data Storage

- **S3**: Audio file storage
- **PostgreSQL**: Questionnaire definitions and metadata
- **DynamoDB**: Conversation messages and real-time data
- **SQS**: Message queuing between Lambda functions

## Project Structure

```
questionnaire-processor/
├── lambdas/                    # Lambda function handlers
│   ├── audio_importer/
│   ├── file_watcher/
│   ├── audio_transcriber/
│   ├── conversation_parser/
│   └── questionnaire_processor/
├── shared/                     # Shared utilities and models
│   ├── models/                 # Data models
│   ├── utils/                  # Utilities and configuration
│   ├── database/              # Database clients
│   └── aws_clients/           # AWS service clients
├── tests/                      # Test suite
├── deployment/                 # Deployment configuration
│   ├── serverless.yml         # Serverless Framework config
│   └── requirements.txt       # Lambda dependencies
└── main.py                     # Local development entry point
```

## Installation

### Development Setup

```bash
# Install dependencies
make install-dev

# Or manually:
pip install -r requirements.txt
pip install -e ".[dev]"
```

### Deployment Setup

```bash
cd deployment
npm install
```

## Configuration

Set the following environment variables:

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export STAGE=dev

# Database Configuration  
export POSTGRES_HOST=your-postgres-host
export POSTGRES_USER=your-username
export POSTGRES_PASSWORD=your-password
export POSTGRES_DB=questionnaire_processor

# UContact API
export UCONTACT_API_URL=https://api.ucontact.com
export UCONTACT_API_KEY=your-api-key
```

## Usage

### Local Development

```bash
# Run main script
python main.py

# Run tests
make test

# Lint code
make lint

# Format code
make format
```

### Deployment

```bash
# Deploy to development
make deploy-dev

# Deploy to production
make deploy-prod

# View logs
make logs FUNC=audioImporter

# Remove deployment
make remove
```

## Database Libraries

The project uses **SQLAlchemy** for PostgreSQL operations:

- **SQLAlchemy Core**: For raw SQL queries and schema management
- **SQLAlchemy ORM**: For object-relational mapping
- **psycopg2**: PostgreSQL adapter

For DynamoDB operations, the project uses **boto3** with custom client wrappers.

## Development

### Adding New Lambda Functions

1. Create handler in `lambdas/new_function/handler.py`
2. Add function configuration to `deployment/serverless.yml`
3. Add any new dependencies to `requirements.txt`
4. Update IAM permissions as needed

### Adding New Models

1. Create model classes in `shared/models/`
2. Add corresponding database schemas
3. Write tests in `tests/test_models.py`

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run with coverage
pytest --cov=shared tests/
```

## License

MIT License