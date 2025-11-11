import io
import os

import boto3
from PIL import Image

s3 = boto3.client("s3")


def lambda_handler(event, context):
    record = event["Records"][0]
    src_bucket = record["s3"]["bucket"]["name"]
    src_key = record["s3"]["object"]["key"]
    dst_bucket = os.environ["OUTPUT_BUCKET"]
    dst_key = f"processed/{src_key}"

    # Download
    file_stream = io.BytesIO()
    s3.download_fileobj(src_bucket, src_key, file_stream)
    file_stream.seek(0)

    # Process (example: grayscale)
    image = Image.open(file_stream).convert("L")
    output_stream = io.BytesIO()
    image.save(output_stream, format="JPEG")
    output_stream.seek(0)

    # Upload
    s3.upload_fileobj(output_stream, dst_bucket, dst_key)

    print(f"Processed {src_key} -> {dst_key}")
    return {"status": "OK", "output": dst_key}
