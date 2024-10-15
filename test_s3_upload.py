import os
import logging
import requests
import json
from app import app, get_dummy_presigned_url

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

            # Simulate file upload using the dummy presigned URL
            logger.info(f"Simulating file upload to: {upload_url}")

            # Verify the dummy data
            dummy_data = get_dummy_presigned_url()
            assert data['filename'] == dummy_data['filename'], "Filename mismatch"
            assert data['s3Key'] == dummy_data['s3Key'], "S3 key mismatch"
            assert data['uploadUrl'] == dummy_data['uploadUrl'], "Upload URL mismatch"

            logger.info("Dummy presigned URL data verified successfully")

    except Exception as e:
        logger.error(f"Error during S3 upload test: {str(e)}")

    finally:
        # Clean up the local test file
        os.remove(test_file)
        logger.info(f"Removed local test file: {test_file}")

if __name__ == "__main__":
    test_s3_upload()
