import os
import logging
import requests
import json
from app import app, init_s3_client, S3_BUCKET, S3_REGION, test_aws_credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_file():
    filename = "test_upload.txt"
    content = "This is a test file for S3 upload."
    with open(filename, "w") as f:
        f.write(content)
    return filename

def test_s3_upload():
    logger.info("Starting S3 upload test")

    # Initialize S3 client
    s3_client = init_s3_client()
    if not s3_client:
        logger.error("Failed to initialize S3 client. Aborting upload test.")
        return

    # Log S3 client initialization
    logger.info(f"S3 client initialized with region: {S3_REGION}")
    logger.info(f"Using S3 bucket: {S3_BUCKET}")

    # Test AWS credentials
    creds_test_result, creds_test_message = test_aws_credentials()
    logger.info(f"AWS credentials test result: {creds_test_result}")
    logger.info(f"AWS credentials test message: {creds_test_message}")

    if not creds_test_result:
        logger.error("AWS credentials test failed. Aborting upload test.")
        return

    # Create test file
    test_file = create_test_file()
    logger.info(f"Created test file: {test_file}")

    try:
        # Test get-upload-url endpoint
        with app.test_client() as client:
            response = client.post('/get-upload-url', json={
                'fileName': test_file,
                'fileType': 'text/plain'
            })
            
            if response.status_code != 200:
                logger.error(f"Failed to get upload URL. Status code: {response.status_code}")
                return

            data = json.loads(response.data)
            upload_url = data['uploadUrl']
            s3_key = data['s3Key']
            logger.info(f"Received upload URL and S3 key: {s3_key}")

            # Upload file using the pre-signed URL
            with open(test_file, 'rb') as f:
                upload_response = requests.put(upload_url, data=f.read(), headers={'Content-Type': 'text/plain'})
            
            if upload_response.status_code != 200:
                logger.error(f"Failed to upload file. Status code: {upload_response.status_code}")
                return

            logger.info("File uploaded successfully using pre-signed URL")

            # Verify file accessibility
            try:
                response = s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
                logger.info(f"File verification successful. File size: {response['ContentLength']} bytes")
            except Exception as e:
                logger.error(f"Error verifying uploaded file: {str(e)}")

    except Exception as e:
        logger.error(f"Error during S3 upload test: {str(e)}")

    finally:
        # Clean up the local test file
        os.remove(test_file)
        logger.info(f"Removed local test file: {test_file}")

if __name__ == "__main__":
    test_s3_upload()
