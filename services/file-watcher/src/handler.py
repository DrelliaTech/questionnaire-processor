import os
import json
import logging
from typing import Any, Dict
from datetime import datetime
import boto3

from drellia_utils.src.aws import SQSClient
from drellia_models.src.conversation import TranscriptionJob

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AUDIO_TRANSCRIPTION_QUEUE_URL = os.environ.get("AUDIO_TRANSCRIPTION_QUEUE_URL")
SUPPORTED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".webm"]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler triggered by S3 events when new files are uploaded.
    Queues audio files for transcription.
    """
    try:
        sqs_client = SQSClient(queue_url=AUDIO_TRANSCRIPTION_QUEUE_URL)
        processed_count = 0
        error_count = 0
        
        for record in event.get("Records", []):
            try:
                # Extract S3 event details
                s3_event = record.get("s3", {})
                bucket_name = s3_event.get("bucket", {}).get("name")
                object_key = s3_event.get("object", {}).get("key")
                object_size = s3_event.get("object", {}).get("size")
                
                if not bucket_name or not object_key:
                    logger.error(f"Missing bucket or key in record: {record}")
                    error_count += 1
                    continue
                
                # Check if file has supported audio extension
                file_extension = os.path.splitext(object_key)[1].lower()
                if file_extension not in SUPPORTED_EXTENSIONS:
                    logger.info(f"Skipping non-audio file: {object_key}")
                    continue
                
                # Create transcription job
                job = TranscriptionJob(
                    id=f"{bucket_name}/{object_key}/{datetime.utcnow().timestamp()}",
                    s3_key=f"s3://{bucket_name}/{object_key}",
                    status="pending",
                    created_at=datetime.utcnow(),
                    metadata={
                        "file_size": object_size,
                        "file_extension": file_extension
                    }
                )
                
                # Send to SQS queue
                message_id = sqs_client.send_message(job.model_dump())
                logger.info(f"Queued transcription job for {object_key}, message ID: {message_id}")
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing record: {e}", exc_info=True)
                error_count += 1
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "processed": processed_count,
                "errors": error_count
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }