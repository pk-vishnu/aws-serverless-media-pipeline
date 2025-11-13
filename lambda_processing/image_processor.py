import io
import os

import boto3
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

s3 = boto3.client("s3")


# -----------------------------------------
# Helpers
# -----------------------------------------
def safe_open_image(stream, max_resolution=4096):
    """
    Open an image with memory-optimized decoding.
    draft() reduces decoded resolution before load().
    """
    img = Image.open(stream)

    try:
        img.draft("RGB", (max_resolution, max_resolution))
    except Exception:
        pass

    # Ensure EXIF rotation is applied with minimal copy
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    return img


def apply_operation(image, operation: str, fmt: str):
    """
    Optimized version:
    - No multiple copies
    - Convert in-place when possible
    """

    # --- grayscale ---
    if operation == "grayscale":
        return image.convert("L"), "JPEG"

    # --- thumbnail ---
    elif operation == "thumbnail":
        image.thumbnail((200, 200))
        return image, fmt

    # --- blur ---
    elif operation == "blur":
        return image.filter(ImageFilter.GaussianBlur(5)), fmt

    # --- edges ---
    elif operation == "edges":
        img = image.convert("L") if image.mode != "L" else image
        return img.filter(ImageFilter.FIND_EDGES), "JPEG"

    # --- enhance contrast ---
    elif operation == "enhance":
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(1.5), fmt

    # --- sepia ---
    elif operation == "sepia":
        sepia = (0.393, 0.769, 0.189, 0, 0.349, 0.686, 0.168, 0, 0.272, 0.534, 0.131, 0)
        img = image.convert("RGB", sepia)
        return img, "JPEG"

    # --- crop/pad to 9:16 ---
    elif operation == "crop_pad":
        w, h = image.size
        target_ratio = 9 / 16
        current_ratio = w / h

        if current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = image.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = image.crop((0, top, w, top + new_h))

        return img, fmt

    else:
        print(f"Unknown op {operation}, skipping.")
        return image, fmt


def save_and_upload(image, bucket, key, fmt):
    out = io.BytesIO()
    image.save(out, format=fmt)
    out.seek(0)

    s3.upload_fileobj(
        out,
        bucket,
        key,
        ExtraArgs={"ContentType": Image.MIME.get(fmt, "image/jpeg")},
    )


# -----------------------------------------
# Lambda Handler
# -----------------------------------------
def lambda_handler(event, context):
    try:
        record = event["Records"][0]
        src_bucket = record["s3"]["bucket"]["name"]
        src_key = record["s3"]["object"]["key"]
        dst_bucket = os.environ["OUTPUT_BUCKET"]

        base_name, ext = os.path.splitext(src_key)
        sequential_key = f"processed/{base_name}_combined{ext}"

        # --- Get metadata ---
        try:
            metadata = s3.head_object(Bucket=src_bucket, Key=src_key).get(
                "Metadata", {}
            )
        except:
            metadata = {}

        operations = [
            o.strip()
            for o in metadata.get("operations", "grayscale").split(",")
            if o.strip()
        ]

        # --- Load image in memory-efficient way ---
        stream = io.BytesIO()
        s3.download_fileobj(src_bucket, src_key, stream)
        stream.seek(0)

        original = safe_open_image(stream)
        original_format = (original.format or "JPEG").upper()

        # ----------------------------------
        # SEQUENTIAL PROCESSING
        # ----------------------------------
        img_seq = original.copy()
        fmt_seq = original_format

        for op in operations:
            img_seq, fmt_seq = apply_operation(img_seq, op, fmt_seq)

        save_and_upload(img_seq, dst_bucket, sequential_key, fmt_seq)
        img_seq.close()

        # ----------------------------------
        # INDEPENDENT PROCESSING
        # ----------------------------------
        for op in operations:
            img_ind = original.copy()
            fmt_ind = original_format

            img_ind, fmt_ind = apply_operation(img_ind, op, fmt_ind)
            ind_key = f"processed/{base_name}_{op}{ext}"

            save_and_upload(img_ind, dst_bucket, ind_key, fmt_ind)
            img_ind.close()

        original.close()
        return {"status": "OK", "output": sequential_key}

    except Exception as e:
        print(f"Fatal: {e}")
        raise e
