import io
import os

import boto3
from PIL import Image, ImageFilter

s3 = boto3.client("s3")


def apply_operation(image: Image.Image, operation: str, current_format: str):
    """
    Applies a single operation to a PIL Image object.
    Returns the modified image and its new format.
    """
    output_format = current_format

    if operation == "grayscale":
        image = image.convert("L")
        output_format = "JPEG"

    elif operation == "thumbnail":
        image.thumbnail((200, 200))

    elif operation == "blur":
        image = image.filter(ImageFilter.GaussianBlur(radius=5))

    elif operation == "edges":
        # Edge detection requires grayscale
        if image.mode != "L":
            image = image.convert("L")
        image = image.filter(ImageFilter.FIND_EDGES)
        output_format = "JPEG"

    else:
        print(f"Warning: Unknown operation '{operation}'. Skipping.")
        # Return None to indicate a skipped/unknown operation
        return None, output_format

    return image, output_format


def save_and_upload(image: Image.Image, bucket: str, key: str, format: str):
    """
    Saves a PIL Image to an in-memory buffer and uploads it to S3.
    """
    try:
        output_stream = io.BytesIO()
        image.save(output_stream, format=format)
        output_stream.seek(0)

        # Get content type for browser viewing
        content_type = Image.MIME.get(format, "image/jpeg")

        s3.upload_fileobj(
            output_stream,
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        print(f"Successfully uploaded: {key}")
    except Exception as e:
        print(f"Error uploading {key}: {e}")


def lambda_handler(event, context):
    try:
        # 1. Get Event Details
        record = event["Records"][0]
        src_bucket = record["s3"]["bucket"]["name"]
        src_key = record["s3"]["object"]["key"]

        dst_bucket = os.environ["OUTPUT_BUCKET"]

        base_name, extension = os.path.splitext(src_key)

        # Sequentially processed (combined fx) file
        sequential_dst_key = f"processed/{base_name}_combined{extension}"

        # 2. Get Operation from Metadata
        metadata = {}
        try:
            head_response = s3.head_object(Bucket=src_bucket, Key=src_key)
            metadata = head_response.get("Metadata", {})
            print(f"Successfully fetched metadata: {metadata}")
        except Exception as e:
            print(f"Error fetching head_object, using default. Error: {e}")

        operations_string = metadata.get("operations", "grayscale")
        operations_list = [
            op.strip() for op in operations_string.split(",") if op.strip()
        ]

        # 3. Download Image
        file_stream = io.BytesIO()
        s3.download_fileobj(src_bucket, src_key, file_stream)
        file_stream.seek(0)

        original_image = Image.open(file_stream)
        original_format = original_image.format or "JPEG"

        # --- 4a. Sequential Processing  ---
        print(f"Applying sequential operations: {operations_list}")
        sequential_image = original_image.copy()
        seq_format = original_format

        for op in operations_list:
            img, fmt = apply_operation(sequential_image, op, seq_format)
            if img:
                sequential_image = img
                seq_format = fmt

        save_and_upload(sequential_image, dst_bucket, sequential_dst_key, seq_format)

        # --- 4b. Independent Processing  ---
        print(f"Applying independent operations...")
        for op in operations_list:
            ind_image = original_image.copy()
            ind_format = original_format

            print(f"Applying independent op: {op}")
            img, fmt = apply_operation(ind_image, op, ind_format)

            if img:
                ind_key = f"processed/{base_name}_{op}{extension}"
                save_and_upload(img, dst_bucket, ind_key, fmt)

        # only returning combined fx image for analyser
        print(f"Processing complete. Main output: {sequential_dst_key}")
        return {"status": "OK", "output": sequential_dst_key}

    except Exception as e:
        print(f"Error processing image: {e}")
        raise e
