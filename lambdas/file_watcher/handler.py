"""
File Watcher Lambda
Triggered by S3 events to queue audio files for transcription
"""
import json
import boto3
from typing import Dict, Any


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for file watcher Lambda function
    Processes S3 events and queues files for transcription
    """
    try:
        sqs = boto3.client('sqs')
        
        # Process S3 event records
        for record in event.get('Records', []):
            if record.get('eventSource') == 'aws:s3':
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                
                # TODO: Queue message to AudioTranscriptionQueue
                
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Files queued for transcription',
                'processed_records': len(event.get('Records', []))
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }