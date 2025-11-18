"""
vote.py - Lambda Function for Processing Survey Votes

WHAT THIS FILE DOES:
This is an AWS Lambda function that handles POST requests when users submit their votes
in the survey. It stores the vote in a DynamoDB database.

KEY CONCEPTS FOR STUDENTS:
1. AWS Lambda: Serverless computing - code runs without managing servers
2. DynamoDB: AWS's NoSQL database service (key-value store)
3. API Integration: This function is triggered by API Gateway when users click vote buttons
4. Environment Variables: Configuration passed to the function at runtime
5. Error Handling: Try/except blocks to gracefully handle failures

WORKFLOW:
User clicks vote button → API Gateway receives request → This Lambda runs → Data saved to DynamoDB
"""

import json  # Python's built-in library for parsing JSON data
import boto3  # AWS SDK for Python - allows us to interact with AWS services
import os  # Access to operating system features like environment variables

# STEP 1: Set up connection to DynamoDB
# boto3.resource creates a high-level interface to DynamoDB
dynamodb = boto3.resource('dynamodb')

# STEP 2: Get the table name from environment variable
# Lambda functions use environment variables for configuration (set in Terraform)
table_name = os.environ.get('DYNAMODB_TABLE')

# STEP 3: Create a reference to our specific DynamoDB table
table = dynamodb.Table(table_name)

def handler(event, context):
    """
    Main Lambda handler function - AWS calls this when the function is invoked.
    
    PARAMETERS:
    - event: Dictionary containing request data (body, headers, etc.) from API Gateway
    - context: Runtime information about the Lambda execution (request ID, time remaining, etc.)
    
    PRIVACY NOTE:
    The sessionId is a temporary identifier stored in the browser's sessionStorage.
    It expires when the user closes their browser tab, respecting user privacy while
    preventing duplicate votes within a single browsing session.
    
    RETURNS:
    Dictionary with statusCode, headers, and body (formatted as API Gateway expects)
    """
    try:
        # STEP 4: Parse the incoming JSON request body
        # event.get('body', '{}') gets the request body, or '{}' if none exists
        # json.loads converts the JSON string into a Python dictionary
        body = json.loads(event.get('body', '{}'))
        
        # STEP 5: Extract the vote choice and session ID from the request
        vote_option = body.get('vote')  # Will be 'no', 'aws', or 'other'
        session_id = body.get('sessionId')  # Unique identifier for this browser session

        # STEP 6: Validate that session ID was provided
        # Without this, users could vote multiple times by refreshing the page
        if not session_id:
            return {
                'statusCode': 400,  # 400 = Bad Request (client error)
                'headers': {
                    # CORS header allows requests from any domain (the '*' wildcard)
                    # This is needed for the browser to accept the response
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                },
                'body': json.dumps({'message': 'Session ID is required'})
            }

        # STEP 7: Validate that the vote option is one we expect
        # This prevents someone from submitting invalid data through the API
        if vote_option not in ['no', 'aws', 'other']:
            return {
                'statusCode': 400,  # 400 = Bad Request
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                },
                'body': json.dumps({'message': 'Invalid vote option'})
            }

        # STEP 8: Create the item to store in DynamoDB
        # In DynamoDB, each item must have a primary key (here it's 'id')
        # If an item with this ID already exists, it will be overwritten (allowing vote changes)
        item = {
            'id': session_id,      # Primary key - must be unique
            'vote': vote_option    # The user's choice: 'no', 'aws', or 'other'
        }

        # STEP 9: Store the vote in DynamoDB
        # put_item either creates a new item or replaces an existing one with the same key
        table.put_item(Item=item)

        # STEP 10: Return success response to the browser
        return {
            'statusCode': 200,  # 200 = OK (success)
            'headers': {
                # CORS headers are required for browser to accept the response
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': json.dumps({'message': 'Vote recorded successfully'})
        }

    except Exception as e:
        # STEP 11: Handle any unexpected errors
        # Print the error to CloudWatch Logs for debugging
        print(f"Error: {e}")
        
        # Return a generic error message to the user
        # (Don't expose internal error details to users - security best practice)
        return {
            'statusCode': 500,  # 500 = Internal Server Error
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': json.dumps({'message': 'Internal server error'})
        }
