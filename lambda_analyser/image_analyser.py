import io
import os

import boto3
from PIL import Image, ImageDraw

s3 = boto3.client("s3")
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]


def create_histogram(image, title):
    """
    Create a simple, Lambda-safe RGB histogram with X/Y axes.
    Uses only the default bitmap font to avoid memory issues.
    """

    # Create a small copy for histogram calculation to save memory
    img_thumb = image.copy()
    img_thumb.thumbnail((1024, 1024))
    img_rgb = img_thumb.convert("RGB")

    # --- Define Layout & Margins ---
    canvas_width = 572
    canvas_height = 300

    margin = {"top": 40, "bottom": 40, "left": 50, "right": 10}

    # Calculate the graph area dimensions
    graph_width = canvas_width - margin["left"] - margin["right"]  # 512px
    graph_height = canvas_height - margin["top"] - margin["bottom"]  # 220px

    # Define the "floor" and "wall" of the graph
    graph_floor_y = margin["top"] + graph_height
    graph_wall_x = margin["left"]

    # Create output canvas
    canvas = Image.new(
        "RGB", (canvas_width, canvas_height), (31, 41, 55)
    )  # bg-gray-800
    draw = ImageDraw.Draw(canvas)

    # --- Compute Histograms ---
    red_hist = img_rgb.histogram()[0:256]
    green_hist = img_rgb.histogram()[256:512]
    blue_hist = img_rgb.histogram()[512:768]

    # --- Normalize Values ---
    max_val = max(max(red_hist), max(green_hist), max(blue_hist))

    # Add safety check for ZeroDivisionError (e.g., a pure black image)
    if max_val == 0:
        scale = 0
    else:
        scale = graph_height / max_val

    # --- Draw Axis Lines ---
    axis_color = (150, 150, 165)  # Light gray for axes
    # Y-Axis Line
    draw.line(
        [(graph_wall_x, margin["top"]), (graph_wall_x, graph_floor_y)], fill=axis_color
    )
    # X-Axis Line
    draw.line(
        [(graph_wall_x, graph_floor_y), (graph_wall_x + graph_width, graph_floor_y)],
        fill=axis_color,
    )

    # --- Draw R, G, B Line Histograms ---
    # We now plot relative to the graph_wall_x and graph_floor_y
    x_step = graph_width / 255.0  # Use float for precision

    for i in range(255):
        # Calculate x coordinates
        x1 = graph_wall_x + i * x_step
        x2 = graph_wall_x + (i + 1) * x_step

        # Calculate y coordinates (inverted, 0 is at the top)
        y1_r = graph_floor_y - red_hist[i] * scale
        y2_r = graph_floor_y - red_hist[i + 1] * scale

        y1_g = graph_floor_y - green_hist[i] * scale
        y2_g = graph_floor_y - green_hist[i + 1] * scale

        y1_b = graph_floor_y - blue_hist[i] * scale
        y2_b = graph_floor_y - blue_hist[i + 1] * scale

        # Draw lines
        draw.line([(x1, y1_r), (x2, y2_r)], fill=(255, 80, 80))
        draw.line([(x1, y1_g), (x2, y2_g)], fill=(80, 255, 80))
        draw.line([(x1, y1_b), (x2, y2_b)], fill=(80, 80, 255))

    # --- Add Title & Labels (Using default font) ---
    label_color = (200, 200, 200)

    # Title
    draw.text((margin["left"], 10), title, fill=label_color)

    # X-Axis Labels
    draw.text((graph_wall_x, graph_floor_y + 5), "0", fill=label_color)
    x_mid = graph_wall_x + (128 * x_step)
    draw.text((x_mid - 10, graph_floor_y + 5), "128", fill=label_color)
    x_end = graph_wall_x + (255 * x_step)
    draw.text((x_end - 18, graph_floor_y + 5), "255", fill=label_color)

    # Y-Axis Labels
    draw.text(
        (margin["left"] - 30, margin["top"] - 6), str(int(max_val)), fill=label_color
    )
    draw.text((margin["left"] - 30, graph_floor_y - 6), "0", fill=label_color)

    # --- Save to Buffer ---
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
