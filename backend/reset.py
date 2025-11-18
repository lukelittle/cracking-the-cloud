"""
reset.py - Lambda Function for Resetting Survey Data

WHAT THIS FILE DOES:
This Lambda function handles POST requests to delete all votes from the database.
It's a "reset" or "clear all data" function that removes every item from the DynamoDB table.

KEY CONCEPTS FOR STUDENTS:
1. Batch Operations: Efficiently deleting multiple items at once
2. Table Scanning: Reading all items before deleting them (you need the keys)
3. Pagination: Handling large datasets that exceed one response
4. Batch Writer: DynamoDB feature for bulk write/delete operations

IMPORTANT NOTE:
This is a destructive operation! All survey data is permanently deleted.
In production apps, you'd typically add authentication/authorization here.

WORKFLOW:
Admin clicks reset button → API Gateway calls this Lambda → Lambda scans table for all IDs →
Batch delete removes all items → Success response sent back
"""

import json  # For JSON parsing and creation
import boto3  # AWS SDK for Python
import os  # For environment variables

# STEP 1: Set up DynamoDB connection
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE')
table = dynamodb.Table(table_name)

def handler(event, context):
    """
    Main Lambda handler - deletes all items from the survey table.
    
    NOTE ON METHOD VALIDATION:
    We don't check the HTTP method here because API Gateway is configured to only
    route POST requests to this function (see Terraform: route_key = "POST /reset").
    This is more efficient than checking in the code.
    
    RETURNS:
    Success message if reset completes, error message if it fails
    """
    try:
        # STEP 2: Scan the table to get all item IDs
        # We only need the IDs (primary keys) to delete items
        # ProjectionExpression='id' means "only return the id field"
        scan_response = table.scan(ProjectionExpression='id')
        items = scan_response.get('Items', [])

        # STEP 3: Handle pagination for large tables
        # DynamoDB returns max 1MB of data per scan
        # If there's more data, LastEvaluatedKey will be present
        while 'LastEvaluatedKey' in scan_response:
            # Continue scanning from where we left off
            scan_response = table.scan(
                ProjectionExpression='id',
                ExclusiveStartKey=scan_response['LastEvaluatedKey']
            )
            # Add the new items to our list
            items.extend(scan_response.get('Items', []))

        # STEP 4: Delete all items using batch writer
        # Only proceed if there are items to delete
        if items:
            # batch_writer() is a context manager that handles batching automatically
            # It groups deletes into batches of 25 (DynamoDB's limit) and retries failures
            with table.batch_writer() as batch:
                for item in items:
                    # delete_item needs the primary key ('id' in our case)
                    batch.delete_item(Key={'id': item['id']})
            
            # At this point, all batches have been processed
            # The context manager ensures all writes complete before continuing

        # STEP 5: Return success response
        return {
            'statusCode': 200,  # 200 = OK
            'headers': {
                # CORS headers allow browser to receive response
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
            },
            'body': json.dumps({'message': 'Survey reset successfully'})
        }

    except Exception as e:
        # STEP 6: Handle errors
        print(f"Error: {e}")  # Log to CloudWatch for debugging
        
        # Return error response
        return {
            'statusCode': 500,  # 500 = Internal Server Error
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': json.dumps({'message': 'Internal server error during reset'})
        }
