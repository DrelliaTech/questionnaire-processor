import os
from typing import Any, Dict, List, Optional
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


class DynamoDBClient:
    def __init__(self, table_name: str, region: str = None):
        self.region = region or os.environ.get("AWS_REGION", "eu-north-1")
        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table(table_name)
    
    def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self.table.put_item(Item=item)
            return response
        except ClientError as e:
            raise Exception(f"Error putting item to DynamoDB: {e}")
    
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            raise Exception(f"Error getting item from DynamoDB: {e}")
    
    def query(
        self,
        partition_key: str,
        partition_value: Any,
        sort_key: Optional[str] = None,
        sort_value: Optional[Any] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        try:
            key_condition = Key(partition_key).eq(partition_value)
            if sort_key and sort_value:
                key_condition = key_condition & Key(sort_key).eq(sort_value)
            
            kwargs = {"KeyConditionExpression": key_condition}
            if limit:
                kwargs["Limit"] = limit
            
            response = self.table.query(**kwargs)
            return response.get("Items", [])
        except ClientError as e:
            raise Exception(f"Error querying DynamoDB: {e}")
    
    def batch_write(self, items: List[Dict[str, Any]]) -> None:
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
        except ClientError as e:
            raise Exception(f"Error batch writing to DynamoDB: {e}")
    
    def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_values: Dict[str, Any],
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            kwargs = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_values,
                "ReturnValues": "ALL_NEW"
            }
            if condition_expression:
                kwargs["ConditionExpression"] = condition_expression
            
            response = self.table.update_item(**kwargs)
            return response.get("Attributes", {})
        except ClientError as e:
            raise Exception(f"Error updating item in DynamoDB: {e}")