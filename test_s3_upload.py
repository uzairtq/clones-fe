import os
import logging
import requests
import json
from app import app, generate_presigned_url

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

            # Simulate file upload using the presigned URL
            logger.info(f"Simulating file upload to: {upload_url}")

            with open(test_file, 'rb') as f:
                files = {'file': (test_file, f)}
                upload_response = requests.put(upload_url, data=files['file'])

            if upload_response.status_code == 200:
                logger.info("File uploaded successfully")
            else:
                logger.error(f"Failed to upload file. Status code: {upload_response.status_code}")

    except Exception as e:
        logger.error(f"Error during S3 upload test: {str(e)}")

    finally:
        # Clean up the local test file
        os.remove(test_file)
        logger.info(f"Removed local test file: {test_file}")

if __name__ == "__main__":
    test_s3_upload()
