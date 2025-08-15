#!/usr/bin/env python3
import os
import aws_cdk as cdk
from infrastructure.infrastructure_stack import DrelliaAuditStack

app = cdk.App()

# Get environment from context or command line
environment = app.node.try_get_context("environment") or os.getenv("ENVIRONMENT", "DEV")

# Account mapping
ACCOUNTS = {
    "DEVOPS": "151508346231",
    "DEV": "505825010410",
    "PROD": "469656055410",
}

# ECR is always in DevOps account
ECR_ACCOUNT = ACCOUNTS["DEVOPS"]

# Region mapping
REGIONS = {
    "DEVOPS": "eu-north-1",
    "DEV": "eu-north-1",
    "PROD": "eu-north-1",
}

# Validate environment
if environment not in ["DEV", "PROD"]:
    raise ValueError(f"Invalid environment: {environment}. Must be 'DEV' or 'PROD'")

DrelliaAuditStack(
    app,
    f"DrelliaAudit-{environment}",
    environment=environment,
    ecr_account=ECR_ACCOUNT,
    description=(
        f"Drellia Audit infrastructure for {environment} environment. "
        "Includes Lambda functions, Fargate services, SQS queues, and data storage."
    ),
    env=cdk.Environment(
        account=ACCOUNTS[environment],
        region=REGIONS[environment],
    ),
    tags={
        "Environment": environment,
        "Project": "DrelliaAudit",
        "ManagedBy": "CDK"
    }
)

app.synth()