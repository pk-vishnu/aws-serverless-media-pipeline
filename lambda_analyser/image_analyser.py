import io
import os

import boto3
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

s3 = boto3.client("s3")
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]

plt.style.use("dark_background")


def create_histogram(image, title):
    """
    Generates a 3-channel (R, G, B) color histogram plot from a PIL Image.
    """
    img_rgb = image.convert("RGB")
    img_array = np.array(img_rgb)

    # Create a figure
    fig, ax = plt.subplots(figsize=(6, 4))

    # Plot histograms for each channel
    colors = ("r", "g", "b")
    for i, color in enumerate(colors):
        # Calculate histogram for the channel
        histogram = np.histogram(img_array[..., i], bins=256, range=(0, 256))[0]
        ax.plot(histogram, color=color, alpha=0.7)

    # Style the plot
    ax.set_title(title, fontsize=12)
    ax.set_xlim([0, 256])
    ax.set_yticks([])  # Hide y-axis ticks
    ax.set_facecolor("#374151")  # bg-gray-700
    fig.patch.set_facecolor("#1F2937")  # bg-gray-800

    # Set border color
    for spine in ax.spines.values():
        spine.set_edgecolor("#4B5563")  # bg-gray-600

    # Save plot to a in-memory buffer
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)  # Close the figure to free memory
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
