"""
results.py - Lambda Function for Retrieving Survey Results

WHAT THIS FILE DOES:
This Lambda function handles GET requests to retrieve the current vote counts.
It scans the entire DynamoDB table, counts votes for each option, and returns the totals.

KEY CONCEPTS FOR STUDENTS:
1. Table Scanning: Reading all items from a DynamoDB table
2. Pagination: Handling large datasets that don't fit in one response
3. Data Aggregation: Counting items by category using Python's Counter
4. API Responses: Returning JSON data to the frontend

WORKFLOW:
User loads results page → API Gateway calls this Lambda → Lambda scans DynamoDB →
Counts are calculated → Results returned to browser → Chart displays data
"""

import json  # For converting Python data to JSON format
import boto3  # AWS SDK for Python
import os  # For accessing environment variables
from collections import Counter  # Efficient way to count items in a list

# STEP 1: Set up DynamoDB connection
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE')
table = dynamodb.Table(table_name)

def handler(event, context):
    """
    Main Lambda handler - retrieves and counts all votes from DynamoDB.
    
    RETURNS:
    JSON object with vote counts: { "no": X, "aws": Y, "other": Z }
    """
    try:
        # STEP 2: Scan the table to get all votes
        # ProjectionExpression tells DynamoDB to only return the 'vote' field
        # This saves bandwidth and makes the response faster
        response = table.scan(
            ProjectionExpression='vote'
        )
        
        # STEP 3: Get the items from the first page of results
        items = response.get('Items', [])
        
        # STEP 4: Handle pagination for large datasets
        # DynamoDB limits scan results to 1MB per request
        # If there's more data, we need to make additional requests
        # LastEvaluatedKey indicates there's more data to fetch
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression='vote',
                ExclusiveStartKey=response['LastEvaluatedKey']  # Continue from where we left off
            )
            items.extend(response.get('Items', []))  # Add new items to our list

        # STEP 5: Extract just the vote values from items
        # List comprehension: [expression for item in list]
        # Creates a list like: ['no', 'aws', 'aws', 'other', 'no', ...]
        votes = [item['vote'] for item in items]
        
        # STEP 6: Count occurrences of each vote option
        # Counter is like a special dictionary that counts things
        # Example: Counter(['no', 'aws', 'aws']) → {'no': 1, 'aws': 2}
        vote_counts = Counter(votes)

        # STEP 7: Create the results dictionary with default values of 0
        # .get(key, default) returns the count or 0 if that option has no votes yet
        results = {
            'no': vote_counts.get('no', 0),      # Count of "No cloud experience" votes
            'aws': vote_counts.get('aws', 0),    # Count of "Yes, with AWS" votes
            'other': vote_counts.get('other', 0) # Count of "Yes, with other clouds" votes
        }

        # STEP 8: Return the counts to the client (browser)
        return {
            'statusCode': 200,  # 200 = Success
            'headers': {
                # CORS headers allow the browser to receive this response
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': json.dumps(results)  # Convert Python dict to JSON string
        }

    except Exception as e:
        # STEP 9: Handle any errors
        print(f"Error: {e}")  # Log to CloudWatch for debugging
        return {
            'statusCode': 500,  # 500 = Internal Server Error
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': json.dumps({'message': 'Internal server error'})
        }
