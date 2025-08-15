import os
import json
import logging
import tempfile
from datetime import datetime
from typing import Optional
import boto3

from drellia_utils.src.aws import SQSClient, S3Client
from drellia_models.src.conversation import TranscriptionJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIO_TRANSCRIPTION_QUEUE_URL = os.environ.get("AUDIO_TRANSCRIPTION_QUEUE_URL")
CONVERSATION_PARSER_QUEUE_URL = os.environ.get("CONVERSATION_PARSER_QUEUE_URL")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")


class AudioTranscriber:
    def __init__(self):
        self.sqs_input = SQSClient(queue_url=AUDIO_TRANSCRIPTION_QUEUE_URL)
        self.sqs_output = SQSClient(queue_url=CONVERSATION_PARSER_QUEUE_URL)
        self.s3_client = S3Client(bucket_name=S3_BUCKET_NAME)
        self.transcribe_client = boto3.client("transcribe")
    
    def process_message(self, message: dict) -> None:
        """Process a single transcription job from the queue."""
        try:
            # Parse the message
            job_data = json.loads(message["Body"])
            job = TranscriptionJob(**job_data)
            
            logger.info(f"Processing transcription job: {job.id}")
            
            # Start AWS Transcribe job
            transcript_text = self.transcribe_audio(job.s3_key)
            
            if transcript_text:
                # Update job status
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.transcript_text = transcript_text
                
                # Send to conversation parser queue
                self.sqs_output.send_message(job.model_dump())
                logger.info(f"Transcription completed for job: {job.id}")
            else:
                raise Exception("Transcription failed - no text returned")
            
            # Delete message from input queue
            self.sqs_input.delete_message(message["ReceiptHandle"])
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Message will return to queue after visibility timeout
    
    def transcribe_audio(self, s3_uri: str) -> Optional[str]:
        """
        Transcribe audio using AWS Transcribe service.
        """
        try:
            job_name = f"transcription-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
            # Start transcription job
            response = self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": s3_uri},
                MediaFormat=self._get_media_format(s3_uri),
                LanguageCode="en-US",
                Settings={
                    "ShowSpeakerLabels": True,
                    "MaxSpeakerLabels": 10
                }
            )
            
            # Wait for job completion
            while True:
                status = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
                
                if job_status == "COMPLETED":
                    # Get transcript
                    transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                    transcript_response = boto3.client("s3").get_object(
                        Bucket=transcript_uri.split("/")[3],
                        Key="/".join(transcript_uri.split("/")[4:])
                    )
                    transcript_data = json.loads(transcript_response["Body"].read())
                    return transcript_data["results"]["transcripts"][0]["transcript"]
                
                elif job_status == "FAILED":
                    logger.error(f"Transcription job failed: {job_name}")
                    return None
                
                # Wait before checking again
                import time
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            return None
    
    def _get_media_format(self, s3_uri: str) -> str:
        """Determine media format from file extension."""
        extension = os.path.splitext(s3_uri)[1].lower()
        format_map = {
            ".mp3": "mp3",
            ".mp4": "mp4",
            ".wav": "wav",
            ".flac": "flac",
            ".ogg": "ogg",
            ".webm": "webm",
            ".m4a": "mp4"
        }
        return format_map.get(extension, "mp3")
    
    def run(self):
        """Main loop to process messages from the queue."""
        logger.info("Audio Transcriber service started")
        
        while True:
            try:
                # Receive messages from queue
                messages = self.sqs_input.receive_messages(max_messages=1, wait_time=20)
                
                for message in messages:
                    self.process_message(message)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                import time
                time.sleep(10)  # Wait before retrying


if __name__ == "__main__":
    transcriber = AudioTranscriber()
    transcriber.run()