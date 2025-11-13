import io
import os

import boto3
from PIL import Image, ImageEnhance, ImageFilter

s3 = boto3.client("s3")


# -----------------------------------------------------
#  APPLY OPERATION
# -----------------------------------------------------
def apply_operation(image: Image.Image, operation: str, current_format: str):
    output_format = current_format

    # --- grayscale ---
    if operation == "grayscale":
        image = image.convert("L")
        output_format = "JPEG"

    # --- thumbnail ---
    elif operation == "thumbnail":
        image.thumbnail((200, 200))

    # --- blur ---
    elif operation == "blur":
        image = image.filter(ImageFilter.GaussianBlur(5))

    # --- edges ---
    elif operation == "edges":
        if image.mode != "L":
            image = image.convert("L")
        image = image.filter(ImageFilter.FIND_EDGES)
        output_format = "JPEG"

    # --- enhance contrast ---
    elif operation == "enhance":
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

    # --- sepia ---
    elif operation == "sepia":
        image = image.convert("RGB")

        # Fast sepia using matrix transform
        sepia_matrix = (
            0.393,
            0.769,
            0.189,
            0,
            0.349,
            0.686,
            0.168,
            0,
            0.272,
            0.534,
            0.131,
            0,
        )

        image = image.convert("RGB", sepia_matrix)
        output_format = "JPEG"

    # --- crop/pad to 9:16 ---
    elif operation == "crop_pad":
        width, height = image.size
        target_ratio = 9 / 16
        current_ratio = width / height

        if current_ratio > target_ratio:
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            image = image.crop((left, 0, left + new_width, height))
        else:
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            image = image.crop((0, top, width, top + new_height))

    else:
        print(f"Warning: Unknown operation '{operation}', skipping.")
        return None, output_format

    return image, output_format


# -----------------------------------------------------
#  UPLOAD HELPERS
# -----------------------------------------------------
def save_and_upload(image: Image.Image, bucket: str, key: str, format: str):
    try:
        output_stream = io.BytesIO()
        image.save(output_stream, format=format)
        output_stream.seek(0)

        content_type = Image.MIME.get(format, "image/jpeg")

        s3.upload_fileobj(
            output_stream,
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        print(f"Uploaded: {key}")
    except Exception as e:
        print(f"Upload error for {key}: {e}")


# -----------------------------------------------------
#  LAMBDA HANDLER
# -----------------------------------------------------
def lambda_handler(event, context):
    try:
        # Event details
        record = event["Records"][0]
        src_bucket = record["s3"]["bucket"]["name"]
        src_key = record["s3"]["object"]["key"]
        dst_bucket = os.environ["OUTPUT_BUCKET"]

        base_name, extension = os.path.splitext(src_key)
        sequential_dst_key = f"processed/{base_name}_combined{extension}"

        # Metadata → operations list
        try:
            head = s3.head_object(Bucket=src_bucket, Key=src_key)
            metadata = head.get("Metadata", {})
            print(f"Metadata: {metadata}")
        except Exception as e:
            print(f"Metadata fetch failed: {e}")
            metadata = {}

        operations_str = metadata.get("operations", "grayscale")
        operations = [op.strip() for op in operations_str.split(",") if op.strip()]

        # Download original image
        file_stream = io.BytesIO()
        s3.download_fileobj(src_bucket, src_key, file_stream)
        file_stream.seek(0)

        original = Image.open(file_stream)
        original_format = original.format or "JPEG"

        # -------------------------------
        # SEQUENTIAL (combined effects)
        # -------------------------------
        print(f"Sequential ops: {operations}")

        seq_img = original.copy()
        seq_fmt = original_format

        for op in operations:
            img, fmt = apply_operation(seq_img, op, seq_fmt)
            if img:
                seq_img, seq_fmt = img, fmt

        save_and_upload(seq_img, dst_bucket, sequential_dst_key, seq_fmt)

        # -------------------------------
        # INDEPENDENT (per-effect)
        # -------------------------------
        print("Independent ops:")

        for op in operations:
            ind_img = original.copy()
            ind_fmt = original_format

            img, fmt = apply_operation(ind_img, op, ind_fmt)
            if img:
                ind_key = f"processed/{base_name}_{op}{extension}"
                save_and_upload(img, dst_bucket, ind_key, fmt)

        return {"status": "OK", "output": sequential_dst_key}

    except Exception as e:
        print(f"Fatal error: {e}")
        raise e
