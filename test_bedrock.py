import boto3
from dotenv import load_dotenv
import os

load_dotenv()

client = boto3.client(
    'bedrock-runtime',
    region_name='us-east-1',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

response = client.converse(
    modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
    messages=[{
        'role': 'user',
        'content': [{'text': 'Say hello in one word'}]
    }]
)

print(response['output']['message']['content'][0]['text'])