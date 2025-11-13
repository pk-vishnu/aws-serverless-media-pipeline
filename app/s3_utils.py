import logging
import os
import uuid

import boto3
from botocore.exceptions import ClientError, WaiterError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_client = boto3.client("s3")


def get_unique_key(filename):
    """Generates a unique S3 key for a file."""
    ext = os.path.splitext(filename)[1]
    return f"{uuid.uuid4()}{ext}"


def upload_to_s3(file_obj, bucket, key, metadata=None):
    """
    Uploads a file object to an S3 bucket with metadata.

    :param file_obj: File-like object to upload.
    :param bucket: Target S3 bucket.
    :param key: S3 object key (filename).
    :param metadata: Dictionary of metadata to add.
    :return: True on success, False on failure.
    """
    try:
        extra_args = {}
        if metadata:
            # Boto3 handles adding the 'x-amz-meta-' prefix
            extra_args["Metadata"] = metadata

        s3_client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)
        logger.info(
            f"Successfully uploaded {key} to {bucket} with metadata: {metadata}"
        )
        return True
    except ClientError as e:
        logger.error(f"Failed to upload {key} to {bucket}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during upload: {e}")
        return False


def get_presigned_url(bucket, key, expires_in=3600):
    """
    Generates a presigned URL to view an S3 object.

    :param bucket: S3 bucket.
    :param key: S3 object key.
    :param expires_in: URL expiration time in seconds.
    :return: Presigned URL string, or None on failure.
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for {key} in {bucket}: {e}")
        return None


def wait_for_object(bucket, key, timeout=30, delay=2):
    """
    Waits for an object to exist in an S3 bucket.

    :param bucket: S3 bucket.
    :param key: S3 object key.
    :param timeout: Total time to wait in seconds.
    :param delay: Time to wait between checks.
    :raises: TimeoutError if the object doesn't appear in time.
    """
    logger.info(f"Waiting for object {key} in bucket {bucket}...")
    waiter = s3_client.get_waiter("object_exists")
    try:
        waiter.wait(
            Bucket=bucket,
            Key=key,
            WaiterConfig={"Delay": delay, "MaxAttempts": timeout // delay},
        )
        logger.info(f"Object {key} found in {bucket}.")
    except WaiterError:
        logger.error(f"Timeout waiting for object {key} in {bucket}.")
        raise TimeoutError(f"Processing timed out for {key}.")
