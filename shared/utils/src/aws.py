import os
import json
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import ClientError


class SQSClient:
    def __init__(self, queue_url: Optional[str] = None, region: Optional[str] = None):
        self.region = region or os.environ.get("AWS_REGION", "eu-north-1")
        self.sqs = boto3.client("sqs", region_name=self.region)
        self.queue_url = queue_url or os.environ.get("SQS_QUEUE_URL")
        
        if not self.queue_url:
            raise ValueError("Queue URL is required")
    
    def send_message(self, message_body: Dict[str, Any], message_group_id: Optional[str] = None) -> str:
        try:
            kwargs = {
                "QueueUrl": self.queue_url,
                "MessageBody": json.dumps(message_body)
            }
            if message_group_id:
                kwargs["MessageGroupId"] = message_group_id
            
            response = self.sqs.send_message(**kwargs)
            return response["MessageId"]
        except ClientError as e:
            raise Exception(f"Error sending message to SQS: {e}")
    
    def receive_messages(self, max_messages: int = 1, wait_time: int = 20) -> list:
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time,
                MessageAttributeNames=["All"]
            )
            return response.get("Messages", [])
        except ClientError as e:
            raise Exception(f"Error receiving messages from SQS: {e}")
    
    def delete_message(self, receipt_handle: str) -> None:
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
        except ClientError as e:
            raise Exception(f"Error deleting message from SQS: {e}")


class S3Client:
    def __init__(self, bucket_name: Optional[str] = None, region: Optional[str] = None):
        self.region = region or os.environ.get("AWS_REGION", "eu-north-1")
        self.s3 = boto3.client("s3", region_name=self.region)
        self.bucket_name = bucket_name or os.environ.get("S3_BUCKET_NAME")
        
        if not self.bucket_name:
            raise ValueError("Bucket name is required")
    
    def upload_file(self, file_path: str, key: str) -> str:
        try:
            self.s3.upload_file(file_path, self.bucket_name, key)
            return f"s3://{self.bucket_name}/{key}"
        except ClientError as e:
            raise Exception(f"Error uploading file to S3: {e}")
    
    def download_file(self, key: str, file_path: str) -> None:
        try:
            self.s3.download_file(self.bucket_name, key, file_path)
        except ClientError as e:
            raise Exception(f"Error downloading file from S3: {e}")
    
    def get_object(self, key: str) -> bytes:
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            raise Exception(f"Error getting object from S3: {e}")
    
    def put_object(self, key: str, body: bytes, content_type: Optional[str] = None) -> str:
        try:
            kwargs = {
                "Bucket": self.bucket_name,
                "Key": key,
                "Body": body
            }
            if content_type:
                kwargs["ContentType"] = content_type
            
            self.s3.put_object(**kwargs)
            return f"s3://{self.bucket_name}/{key}"
        except ClientError as e:
            raise Exception(f"Error putting object to S3: {e}")
    
    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> list:
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            return response.get("Contents", [])
        except ClientError as e:
            raise Exception(f"Error listing objects in S3: {e}")


class SecretsManagerClient:
    def __init__(self, region: Optional[str] = None):
        self.region = region or os.environ.get("AWS_REGION", "eu-north-1")
        self.client = boto3.client("secretsmanager", region_name=self.region)
    
    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            if "SecretString" in response:
                return json.loads(response["SecretString"])
            else:
                raise Exception("Binary secrets are not supported")
        except ClientError as e:
            raise Exception(f"Error getting secret: {e}")