import io
import os

import boto3
from PIL import Image, ImageDraw

s3 = boto3.client("s3")
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]


def create_histogram(image, title):
    """
    Create a simple RGB histogram image using Pillow.
    """

    img_rgb = image.convert("RGB")
    width, height = 512, 300
    hist_height = 200

    # Create output canvas
    canvas = Image.new("RGB", (width, height), (31, 41, 55))  # bg-gray-800
    draw = ImageDraw.Draw(canvas)

    # Compute histograms
    red_hist = img_rgb.histogram()[0:256]
    green_hist = img_rgb.histogram()[256:512]
    blue_hist = img_rgb.histogram()[512:768]

    # Normalize values to fit into hist_height
    max_val = max(max(red_hist), max(green_hist), max(blue_hist))
    scale = hist_height / max_val

    # Draw R, G, B line histograms
    for i in range(255):
        # red
        draw.line(
            [
                (i * 2, hist_height - red_hist[i] * scale),
                ((i + 1) * 2, hist_height - red_hist[i + 1] * scale),
            ],
            fill=(255, 80, 80),
        )
        # green
        draw.line(
            [
                (i * 2, hist_height - green_hist[i] * scale),
                ((i + 1) * 2, hist_height - green_hist[i + 1] * scale),
            ],
            fill=(80, 255, 80),
        )
        # blue
        draw.line(
            [
                (i * 2, hist_height - blue_hist[i] * scale),
                ((i + 1) * 2, hist_height - blue_hist[i + 1] * scale),
            ],
            fill=(80, 80, 255),
        )

    # Add title
    draw.text((10, hist_height + 10), title, fill=(200, 200, 200))

    # Save to buffer
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf


def lambda_handler(event, context):
    """
    Input event:
    {
        "source_bucket": "input-bucket",
        "source_key": "image.jpg",
        "analysis_key": "analysis/image_original_hist.png",
        "title": "Original Image Histogram"
    }
    """
    try:
        # 1. Get details from the event passed by the Step Function
        source_bucket = event["source_bucket"]
        source_key = event["source_key"]
        analysis_key = event["analysis_key"]
        title = event.get("title", "Color Histogram")

        print(f"Analyzing {source_key} from {source_bucket}")

        # 2. Download Image
        file_stream = io.BytesIO()
        s3.download_fileobj(source_bucket, source_key, file_stream)
        file_stream.seek(0)

        image = Image.open(file_stream)

        # 3. Generate Histogram
        histogram_buffer = create_histogram(image, title)

        # 4. Upload histogram to Output Bucket
        s3.upload_fileobj(
            histogram_buffer,
            OUTPUT_BUCKET,
            analysis_key,
            ExtraArgs={"ContentType": "image/png"},
        )

        print(f"Successfully generated histogram: {analysis_key}")
        return {"status": "OK", "bucket": OUTPUT_BUCKET, "key": analysis_key}

    except Exception as e:
        print(f"Error analyzing image: {e}")
        raise e
