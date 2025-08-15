import os
import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any
import boto3

from drellia_utils.src.aws import SQSClient
from drellia_database.src.dynamodb import DynamoDBClient
from drellia_database.src.postgresql import PostgreSQLClient
from drellia_models.src.conversation import (
    TranscriptionJob,
    Conversation,
    Message,
    ConversationDB,
    Base
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONVERSATION_PARSER_QUEUE_URL = os.environ.get("CONVERSATION_PARSER_QUEUE_URL")
DYNAMODB_MESSAGES_TABLE = os.environ.get("DYNAMODB_MESSAGES_TABLE", "ChatsMessages")


class ConversationParser:
    def __init__(self):
        self.sqs_client = SQSClient(queue_url=CONVERSATION_PARSER_QUEUE_URL)
        self.dynamodb_client = DynamoDBClient(table_name=DYNAMODB_MESSAGES_TABLE)
        self.postgres_client = PostgreSQLClient()
        
        # Create tables if they don't exist
        self.postgres_client.create_tables(Base)
    
    def process_message(self, message: dict) -> None:
        """Process a single transcription job and parse into conversation."""
        try:
            # Parse the message
            job_data = json.loads(message["Body"])
            job = TranscriptionJob(**job_data)
            
            logger.info(f"Processing transcription job: {job.id}")
            
            # Parse transcript into conversation
            conversation = self.parse_transcript(job)
            
            # Store conversation in PostgreSQL
            self.store_conversation_metadata(conversation)
            
            # Store messages in DynamoDB
            self.store_messages(conversation.messages)
            
            logger.info(f"Conversation parsed and stored: {conversation.id}")
            
            # Delete message from queue
            self.sqs_client.delete_message(message["ReceiptHandle"])
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    def parse_transcript(self, job: TranscriptionJob) -> Conversation:
        """
        Parse transcript text into structured conversation.
        This is a simplified version - you may want to add more sophisticated parsing.
        """
        try:
            transcript_text = job.transcript_text or ""
            
            # Generate unique IDs
            conversation_id = str(uuid.uuid4())
            context_id = f"context-{conversation_id}"
            
            # Parse transcript into messages
            # This is a simplified example - you'd want more sophisticated parsing
            messages = []
            
            # Split transcript into speaker segments if available
            segments = self._extract_speaker_segments(transcript_text)
            
            for i, segment in enumerate(segments):
                message = Message(
                    id=str(uuid.uuid4()),
                    context_id=context_id,
                    content=segment["text"],
                    role=segment["speaker"],
                    timestamp=datetime.utcnow(),
                    metadata={
                        "segment_index": i,
                        "confidence": segment.get("confidence", 1.0)
                    }
                )
                messages.append(message)
            
            # Create conversation object
            conversation = Conversation(
                id=conversation_id,
                context_id=context_id,
                transcript_id=job.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                messages=messages,
                metadata={
                    "source_file": job.s3_key,
                    "transcription_completed_at": job.completed_at.isoformat() if job.completed_at else None
                }
            )
            
            return conversation
            
        except Exception as e:
            logger.error(f"Error parsing transcript: {e}", exc_info=True)
            raise
    
    def _extract_speaker_segments(self, transcript_text: str) -> List[Dict[str, Any]]:
        """
        Extract speaker segments from transcript.
        This is a placeholder - implement based on your transcript format.
        """
        # For now, treat entire transcript as single segment
        # In production, you'd parse speaker labels from AWS Transcribe output
        return [{
            "speaker": "speaker_1",
            "text": transcript_text,
            "confidence": 1.0
        }]
    
    def store_conversation_metadata(self, conversation: Conversation) -> None:
        """Store conversation metadata in PostgreSQL."""
        try:
            with self.postgres_client.get_session() as session:
                conversation_db = ConversationDB(
                    id=conversation.id,
                    context_id=conversation.context_id,
                    transcript_id=conversation.transcript_id,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                    metadata=conversation.metadata
                )
                session.add(conversation_db)
                session.commit()
                
        except Exception as e:
            logger.error(f"Error storing conversation metadata: {e}", exc_info=True)
            raise
    
    def store_messages(self, messages: List[Message]) -> None:
        """Store messages in DynamoDB."""
        try:
            items = []
            for message in messages:
                item = {
                    "contextId": message.context_id,
                    "createdAt": int(message.timestamp.timestamp() * 1000),
                    "messageId": message.id,
                    "content": message.content,
                    "role": message.role,
                    "metadata": message.metadata
                }
                items.append(item)
            
            # Batch write to DynamoDB
            self.dynamodb_client.batch_write(items)
            
        except Exception as e:
            logger.error(f"Error storing messages: {e}", exc_info=True)
            raise
    
    def run(self):
        """Main loop to process messages from the queue."""
        logger.info("Conversation Parser service started")
        
        while True:
            try:
                # Receive messages from queue
                messages = self.sqs_client.receive_messages(max_messages=1, wait_time=20)
                
                for message in messages:
                    self.process_message(message)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                import time
                time.sleep(10)


if __name__ == "__main__":
    parser = ConversationParser()
    parser.run()