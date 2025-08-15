import os
import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any
import openai

from drellia_database.src.dynamodb import DynamoDBClient
from drellia_database.src.postgresql import PostgreSQLClient
from drellia_models.src.conversation import (
    Message,
    QuestionnaireResponse,
    QuestionnaireResponseDB,
    ConversationDB,
    Base
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DYNAMODB_MESSAGES_TABLE = os.environ.get("DYNAMODB_MESSAGES_TABLE", "ChatsMessages")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class QuestionnaireProcessor:
    def __init__(self):
        self.dynamodb_client = DynamoDBClient(table_name=DYNAMODB_MESSAGES_TABLE)
        self.postgres_client = PostgreSQLClient()
        openai.api_key = OPENAI_API_KEY
        
        # Ensure tables exist
        self.postgres_client.create_tables(Base)
    
    def process_questionnaire(
        self,
        conversation_id: str,
        questions: List[Dict[str, Any]]
    ) -> List[QuestionnaireResponse]:
        """
        Process a questionnaire against a conversation.
        
        Args:
            conversation_id: ID of the conversation to analyze
            questions: List of questions to answer
        
        Returns:
            List of questionnaire responses
        """
        try:
            # Fetch conversation from PostgreSQL
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"Conversation not found: {conversation_id}")
            
            # Fetch messages from DynamoDB
            messages = self.get_messages(conversation.context_id)
            
            # Process each question
            responses = []
            for question in questions:
                response = self.answer_question(
                    question=question,
                    messages=messages,
                    conversation_id=conversation_id
                )
                responses.append(response)
                
                # Store response in PostgreSQL
                self.store_response(response)
            
            return responses
            
        except Exception as e:
            logger.error(f"Error processing questionnaire: {e}", exc_info=True)
            raise
    
    def get_conversation(self, conversation_id: str) -> Any:
        """Fetch conversation metadata from PostgreSQL."""
        try:
            with self.postgres_client.get_session() as session:
                conversation = session.query(ConversationDB).filter_by(
                    id=conversation_id
                ).first()
                return conversation
                
        except Exception as e:
            logger.error(f"Error fetching conversation: {e}", exc_info=True)
            raise
    
    def get_messages(self, context_id: str) -> List[Message]:
        """Fetch messages from DynamoDB."""
        try:
            items = self.dynamodb_client.query(
                partition_key="contextId",
                partition_value=context_id
            )
            
            messages = []
            for item in items:
                message = Message(
                    id=item["messageId"],
                    context_id=item["contextId"],
                    content=item["content"],
                    role=item["role"],
                    timestamp=datetime.fromtimestamp(item["createdAt"] / 1000),
                    metadata=item.get("metadata", {})
                )
                messages.append(message)
            
            # Sort by timestamp
            messages.sort(key=lambda m: m.timestamp)
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}", exc_info=True)
            raise
    
    def answer_question(
        self,
        question: Dict[str, Any],
        messages: List[Message],
        conversation_id: str
    ) -> QuestionnaireResponse:
        """
        Use OpenAI to answer a question based on conversation messages.
        """
        try:
            # Prepare conversation context
            conversation_text = "\n".join([
                f"{msg.role}: {msg.content}"
                for msg in messages
            ])
            
            # Create prompt
            prompt = f"""
            Based on the following conversation, please answer the question.
            
            Conversation:
            {conversation_text}
            
            Question: {question.get('text', '')}
            
            Instructions: {question.get('instructions', 'Provide a clear and concise answer.')}
            
            Answer:
            """
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are analyzing conversations to answer specific questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            
            # Calculate confidence (simplified - you may want more sophisticated logic)
            confidence = 0.8 if answer else 0.0
            
            return QuestionnaireResponse(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                question_id=question.get("id", str(uuid.uuid4())),
                answer=answer,
                confidence=confidence,
                created_at=datetime.utcnow(),
                metadata={
                    "question_text": question.get("text", ""),
                    "model": "gpt-4"
                }
            )
            
        except Exception as e:
            logger.error(f"Error answering question: {e}", exc_info=True)
            # Return empty response on error
            return QuestionnaireResponse(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                question_id=question.get("id", str(uuid.uuid4())),
                answer="Error: Could not process question",
                confidence=0.0,
                created_at=datetime.utcnow(),
                metadata={"error": str(e)}
            )
    
    def store_response(self, response: QuestionnaireResponse) -> None:
        """Store questionnaire response in PostgreSQL."""
        try:
            with self.postgres_client.get_session() as session:
                response_db = QuestionnaireResponseDB(
                    id=response.id,
                    conversation_id=response.conversation_id,
                    question_id=response.question_id,
                    answer=response.answer,
                    confidence=int(response.confidence * 100),
                    created_at=response.created_at,
                    metadata=response.metadata
                )
                session.add(response_db)
                session.commit()
                
        except Exception as e:
            logger.error(f"Error storing response: {e}", exc_info=True)
            raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for questionnaire processing.
    """
    try:
        processor = QuestionnaireProcessor()
        
        # Extract parameters from event
        conversation_id = event.get("conversation_id")
        questions = event.get("questions", [])
        
        if not conversation_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "conversation_id is required"})
            }
        
        # Process questionnaire
        responses = processor.process_questionnaire(conversation_id, questions)
        
        # Convert responses to JSON-serializable format
        response_data = [
            {
                "id": r.id,
                "question_id": r.question_id,
                "answer": r.answer,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat()
            }
            for r in responses
        ]
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "conversation_id": conversation_id,
                "responses": response_data
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


if __name__ == "__main__":
    # For testing locally
    processor = QuestionnaireProcessor()
    print("Questionnaire Processor initialized")