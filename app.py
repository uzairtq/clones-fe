from flask import Flask, request, jsonify
import logging
import os
import uuid
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB limit

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get('S3_BUCKET')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

s3_client = None

def initialize_s3_client():
    global s3_client
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        # Test the connection by listing buckets
        s3_client.list_buckets()
        logger.info("S3 client initialized successfully")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        return None

s3_client = initialize_s3_client()

def generate_presigned_url(file_name, file_type):
    if not s3_client:
        logger.error("S3 client is not initialized")
        return None, None

    try:
        s3_key = f"user-uploads/{file_name}-{uuid.uuid4().hex}"
        
        response = s3_client.generate_presigned_post(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Fields={"Content-Type": file_type},
            Conditions=[
                {"Content-Type": file_type}
            ],
            ExpiresIn=3600
        )
        
        logger.info(f"Generated presigned URL for multipart upload: {response['url']}")
        return response, s3_key
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        if e.response['Error']['Code'] == 'NoSuchBucket':
            logger.error(f"Bucket '{S3_BUCKET}' does not exist")
        elif e.response['Error']['Code'] == 'AccessDenied':
            logger.error("Access denied. Check your AWS credentials and bucket permissions")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error generating presigned URL: {str(e)}")
        return None, None

@app.route('/get-upload-url', methods=['POST'])
def get_upload_url():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        file_name = data.get('fileName')
        file_type = data.get('fileType')

        if not file_name or not file_type:
            return jsonify({'error': 'fileName and fileType are required'}), 400

        presigned_data, s3_key = generate_presigned_url(file_name, file_type)
        
        if presigned_data and s3_key:
            return jsonify({
                'uploadUrl': presigned_data['url'],
                'fields': presigned_data['fields'],
                's3Key': s3_key
            })
        else:
            return jsonify({'error': 'Failed to generate upload URL'}), 500
    except Exception as e:
        logger.error(f"Error in get_upload_url: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
