import io
import os

import boto3
from PIL import Image, ImageDraw

s3 = boto3.client("s3")
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]


def safe_open_image(stream, max_res=2048):
    img = Image.open(stream)
    try:
        img.draft("RGB", (max_res, max_res))
    except:
        pass
    img.thumbnail((max_res, max_res))
    return img.convert("RGB")


def create_histogram(image, title):
    # Canvas
    W, H = 572, 300
    margin = {"top": 40, "bottom": 40, "left": 50, "right": 10}

    graph_w = W - margin["left"] - margin["right"]
    graph_h = H - margin["top"] - margin["bottom"]

    floor_y = margin["top"] + graph_h
    wall_x = margin["left"]

    canvas = Image.new("RGB", (W, H), (31, 41, 55))
    draw = ImageDraw.Draw(canvas)

    # Histogram (fast)
    hist = image.histogram()
    r = hist[0:256]
    g = hist[256:512]
    b = hist[512:768]

    max_val = max(max(r), max(g), max(b)) or 1
    scale = graph_h / max_val

    x_step = graph_w / 255

    for i in range(255):
        x1 = wall_x + i * x_step
        x2 = wall_x + (i + 1) * x_step

        draw.line(
            [(x1, floor_y - r[i] * scale), (x2, floor_y - r[i + 1] * scale)],
            fill=(255, 80, 80),
        )
        draw.line(
            [(x1, floor_y - g[i] * scale), (x2, floor_y - g[i + 1] * scale)],
            fill=(80, 255, 80),
        )
        draw.line(
            [(x1, floor_y - b[i] * scale), (x2, floor_y - b[i + 1] * scale)],
            fill=(80, 80, 255),
        )

    draw.text((margin["left"], 10), title, fill=(200, 200, 200))
    draw.text((wall_x, floor_y + 5), "0", fill=(200, 200, 200))
    draw.text((wall_x + 128 * x_step - 10, floor_y + 5), "128", fill=(200, 200, 200))
    draw.text((wall_x + 255 * x_step - 18, floor_y + 5), "255", fill=(200, 200, 200))

    out = io.BytesIO()
    canvas.save(out, "PNG")
    out.seek(0)
    return out


def lambda_handler(event, context):
    try:
        bucket = event["source_bucket"]
        key = event["source_key"]
        out_key = event["analysis_key"]
        title = event.get("title", "Histogram")

        stream = io.BytesIO()
        s3.download_fileobj(bucket, key, stream)
        stream.seek(0)

        img = safe_open_image(stream)

        hist_buffer = create_histogram(img, title)

        s3.upload_fileobj(
            hist_buffer,
            OUTPUT_BUCKET,
            out_key,
            ExtraArgs={"ContentType": "image/png"},
        )

        img.close()
        return {"status": "OK", "key": out_key}

    except Exception as e:
        print(f"Error: {e}")
        raise e
