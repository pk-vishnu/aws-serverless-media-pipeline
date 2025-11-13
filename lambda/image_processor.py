import io
import os

import boto3
from PIL import Image, ImageFilter, ImageOps

s3 = boto3.client("s3")


def lambda_handler(event, context):
    try:
        # 1. Get Event Details
        record = event["Records"][0]
        src_bucket = record["s3"]["bucket"]["name"]
        src_key = record["s3"]["object"]["key"]

        # This is where the output file will be saved
        dst_bucket = os.environ["OUTPUT_BUCKET"]
        dst_key = f"processed/{src_key}"

        # 2. Get Operation from Metadata
        metadata = {}  # Default to empty metadata
        try:
            # Make a head_object call to get the object's metadata
            head_response = s3.head_object(Bucket=src_bucket, Key=src_key)
            # The metadata we set is in the 'Metadata' field
            # Boto3 strips our 'x-amz-meta-' prefix, so we just use 'operations'
            metadata = head_response.get("Metadata", {})
            print(f"Successfully fetched metadata: {metadata}")

        except Exception as e:
            print(f"Error fetching head_object, using default. Error: {e}")

        # Get string and split into a list
        # Default to "grayscale" if no metadata is found
        # We use .get() on our new 'metadata' dictionary
        operations_string = metadata.get("operations", "grayscale")

        # Split the string by commas, strip whitespace, and filter out empty strings
        operations_list = [
            op.strip() for op in operations_string.split(",") if op.strip()
        ]

        # 3. Download Image
        file_stream = io.BytesIO()
        s3.download_fileobj(src_bucket, src_key, file_stream)
        file_stream.seek(0)

        image = Image.open(file_stream)

        # Preserve original format, default to JPEG
        output_format = image.format or "JPEG"

        # 4. Process Image based on Operation
        print(f"Processing {src_key} with operations: {operations_list}")

        # --- Loop through operations and apply them sequentially ---
        for operation in operations_list:
            print(f"Applying operation: {operation}")

            if operation == "grayscale":
                image = image.convert("L")
                output_format = "JPEG"

            elif operation == "thumbnail":
                # Create a 200x200 thumbnail
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

        # 5. Save Processed Image to Memory
        output_stream = io.BytesIO()
        image.save(output_stream, format=output_format)
        output_stream.seek(0)

        # 6. Upload to Output Bucket
        s3.upload_fileobj(
            output_stream,
            dst_bucket,
            dst_key,
            # Set content type for browser viewing
            ExtraArgs={"ContentType": Image.MIME.get(output_format, "image/jpeg")},
        )

        print(f"Successfully processed {src_key} -> {dst_key}")
        return {"status": "OK", "output": dst_key}

    except Exception as e:
        print(f"Error processing image: {e}")
        raise e
