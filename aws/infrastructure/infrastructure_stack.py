from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_lambda as lambda_,
    aws_ecr as ecr,
)
from constructs import Construct


class DrelliaAuditStack(Stack):
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        environment: str, 
        ecr_account: str = None, 
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = environment
        self.ecr_account = ecr_account or Stack.of(self).account
        
        # Environment-aware resource naming
        suffix = f"-{self.env_name}"
        
        # Reference existing shared VPC
        vpc = ec2.Vpc.from_lookup(
            self,
            "SharedVPC",
            vpc_name=f"VPC-{self.env_name}"
        )
        
        # S3 Buckets
        audio_bucket = s3.Bucket(
            self,
            "AudioFilesBucket",
            bucket_name=f"drellia-audit-audio{suffix.lower()}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldFiles",
                    expiration=Duration.days(90)
                )
            ]
        )
        
        # DynamoDB Tables (reuse existing pattern from drellia-core)
        chats_messages_table = dynamodb.Table(
            self,
            "ChatsMessagesTable",
            table_name=f"ChatsMessages{suffix}",
            partition_key=dynamodb.Attribute(
                name="contextId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt", type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        # SQS Queues
        audio_transcription_queue = sqs.Queue(
            self,
            "AudioTranscriptionQueue",
            queue_name=f"AudioTranscription{suffix}",
            visibility_timeout=Duration.minutes(15),
            retention_period=Duration.days(14),
            receive_message_wait_time=Duration.seconds(20),
        )
        
        conversation_parser_queue = sqs.Queue(
            self,
            "ConversationParserQueue",
            queue_name=f"ConversationParser{suffix}",
            visibility_timeout=Duration.minutes(10),
            retention_period=Duration.days(14),
            receive_message_wait_time=Duration.seconds(20),
        )
        
        # PostgreSQL RDS
        postgres_sg = ec2.SecurityGroup(
            self,
            "PostgresSG",
            vpc=vpc,
            description="Security group for PostgreSQL RDS instance",
            allow_all_outbound=False
        )
        
        postgres_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access from VPC"
        )
        
        postgres_credentials = rds.DatabaseSecret(
            self,
            "PostgresCredentials",
            username="dbadmin",
            secret_name=f"drellia-audit-postgres{suffix}"
        )
        
        postgres_db = rds.DatabaseInstance(
            self,
            "PostgresDB",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_3
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, 
                ec2.InstanceSize.SMALL
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[postgres_sg],
            database_name="drelliaaudit",
            credentials=postgres_credentials,
            allocated_storage=20,
            backup_retention=Duration.days(7),
            deletion_protection=False if self.env_name == "DEV" else True,
            removal_policy=RemovalPolicy.DESTROY if self.env_name == "DEV" else RemovalPolicy.RETAIN,
        )
        
        # ECR Repositories
        file_watcher_repo = ecr.Repository(
            self,
            "FileWatcherRepo",
            repository_name=f"drellia-audit/file-watcher{suffix.lower()}",
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        audio_transcriber_repo = ecr.Repository(
            self,
            "AudioTranscriberRepo",
            repository_name=f"drellia-audit/audio-transcriber{suffix.lower()}",
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        conversation_parser_repo = ecr.Repository(
            self,
            "ConversationParserRepo",
            repository_name=f"drellia-audit/conversation-parser{suffix.lower()}",
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        questionnaire_processor_repo = ecr.Repository(
            self,
            "QuestionnaireProcessorRepo",
            repository_name=f"drellia-audit/questionnaire-processor{suffix.lower()}",
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        # Lambda Execution Role
        lambda_role = iam.Role(
            self,
            "FileWatcherLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        audio_transcription_queue.grant_send_messages(lambda_role)
        audio_bucket.grant_read(lambda_role)
        
        # File Watcher Lambda
        file_watcher_lambda = lambda_.DockerImageFunction(
            self,
            "FileWatcherLambda",
            function_name=f"FileWatcher{suffix}",
            code=lambda_.DockerImageCode.from_ecr(
                repository=file_watcher_repo,
                tag="latest"
            ),
            memory_size=512,
            timeout=Duration.minutes(5),
            role=lambda_role,
            environment={
                "AUDIO_TRANSCRIPTION_QUEUE_URL": audio_transcription_queue.queue_url,
            }
        )
        
        # Add S3 trigger
        audio_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(file_watcher_lambda)
        )
        
        # ECS Cluster
        cluster = ecs.Cluster(
            self,
            "ECSCluster",
            cluster_name=f"DrelliaAudit{suffix}",
            vpc=vpc,
            container_insights=True
        )
        
        # Fargate Task Definitions and Services
        
        # Audio Transcriber Service
        audio_transcriber_task = ecs.FargateTaskDefinition(
            self,
            "AudioTranscriberTask",
            memory_limit_mib=2048,
            cpu=1024,
        )
        
        audio_transcriber_container = audio_transcriber_task.add_container(
            "AudioTranscriberContainer",
            image=ecs.ContainerImage.from_ecr_repository(
                audio_transcriber_repo,
                "latest"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="audio-transcriber",
                log_retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                "AUDIO_TRANSCRIPTION_QUEUE_URL": audio_transcription_queue.queue_url,
                "CONVERSATION_PARSER_QUEUE_URL": conversation_parser_queue.queue_url,
                "S3_BUCKET_NAME": audio_bucket.bucket_name,
                "AWS_REGION": Stack.of(self).region,
            }
        )
        
        audio_transcription_queue.grant_consume_messages(audio_transcriber_task.task_role)
        conversation_parser_queue.grant_send_messages(audio_transcriber_task.task_role)
        audio_bucket.grant_read(audio_transcriber_task.task_role)
        
        # Grant AWS Transcribe permissions
        audio_transcriber_task.task_role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=[
                    "transcribe:StartTranscriptionJob",
                    "transcribe:GetTranscriptionJob",
                ],
                resources=["*"]
            )
        )
        
        audio_transcriber_service = ecs.FargateService(
            self,
            "AudioTranscriberService",
            cluster=cluster,
            task_definition=audio_transcriber_task,
            desired_count=1,
            service_name=f"audio-transcriber{suffix}",
        )
        
        # Conversation Parser Service
        conversation_parser_task = ecs.FargateTaskDefinition(
            self,
            "ConversationParserTask",
            memory_limit_mib=1024,
            cpu=512,
        )
        
        conversation_parser_container = conversation_parser_task.add_container(
            "ConversationParserContainer",
            image=ecs.ContainerImage.from_ecr_repository(
                conversation_parser_repo,
                "latest"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="conversation-parser",
                log_retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                "CONVERSATION_PARSER_QUEUE_URL": conversation_parser_queue.queue_url,
                "DYNAMODB_MESSAGES_TABLE": chats_messages_table.table_name,
                "POSTGRES_HOST": postgres_db.db_instance_endpoint_address,
                "POSTGRES_PORT": "5432",
                "POSTGRES_DB": "drelliaaudit",
                "AWS_REGION": Stack.of(self).region,
            },
            secrets={
                "POSTGRES_USER": ecs.Secret.from_secrets_manager(postgres_credentials, "username"),
                "POSTGRES_PASSWORD": ecs.Secret.from_secrets_manager(postgres_credentials, "password"),
            }
        )
        
        conversation_parser_queue.grant_consume_messages(conversation_parser_task.task_role)
        chats_messages_table.grant_write_data(conversation_parser_task.task_role)
        
        conversation_parser_service = ecs.FargateService(
            self,
            "ConversationParserService",
            cluster=cluster,
            task_definition=conversation_parser_task,
            desired_count=1,
            service_name=f"conversation-parser{suffix}",
        )
        
        # Questionnaire Processor Lambda
        questionnaire_lambda_role = iam.Role(
            self,
            "QuestionnaireProcessorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        chats_messages_table.grant_read_data(questionnaire_lambda_role)
        
        questionnaire_processor_lambda = lambda_.DockerImageFunction(
            self,
            "QuestionnaireProcessorLambda",
            function_name=f"QuestionnaireProcessor{suffix}",
            code=lambda_.DockerImageCode.from_ecr(
                repository=questionnaire_processor_repo,
                tag="latest"
            ),
            memory_size=1024,
            timeout=Duration.minutes(10),
            role=questionnaire_lambda_role,
            environment={
                "DYNAMODB_MESSAGES_TABLE": chats_messages_table.table_name,
                "POSTGRES_HOST": postgres_db.db_instance_endpoint_address,
                "POSTGRES_PORT": "5432",
                "POSTGRES_DB": "drelliaaudit",
                "AWS_REGION": Stack.of(self).region,
            }
        )
        
        # Add secrets to Lambda
        postgres_credentials.grant_read(questionnaire_processor_lambda)
        
        # Outputs
        CfnOutput(
            self,
            "AudioBucketName",
            value=audio_bucket.bucket_name,
            description="S3 bucket for audio files"
        )
        
        CfnOutput(
            self,
            "AudioTranscriptionQueueUrl",
            value=audio_transcription_queue.queue_url,
            description="SQS queue for audio transcription jobs"
        )
        
        CfnOutput(
            self,
            "ConversationParserQueueUrl",
            value=conversation_parser_queue.queue_url,
            description="SQS queue for conversation parsing jobs"
        )
        
        CfnOutput(
            self,
            "PostgresEndpoint",
            value=postgres_db.db_instance_endpoint_address,
            description="PostgreSQL database endpoint"
        )
        
        CfnOutput(
            self,
            "QuestionnaireProcessorFunctionName",
            value=questionnaire_processor_lambda.function_name,
            description="Questionnaire processor Lambda function name"
        )