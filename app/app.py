import os
import time
from io import BytesIO

import boto3
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

# Load bucket names from environment variables
INPUT_BUCKET = os.getenv("INPUT_BUCKET", "your-input-bucket")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET", "your-output-bucket")

s3 = boto3.client("s3")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["file"]
        effects = request.form.getlist("effects")  # e.g., ['gray', 'blur']
        suffix = "_" + "_".join(effects) if effects else ""
        filename = os.path.splitext(file.filename)[0] + suffix + ".jpg"

        s3.upload_fileobj(file, INPUT_BUCKET, filename)
        print(f"Uploaded {filename} with effects: {effects}")

        # Wait until Lambda processes and writes to output bucket
        output_key = f"processed/{filename}"
        for _ in range(30):  # poll up to ~30 seconds
            try:
                s3.head_object(Bucket=OUTPUT_BUCKET, Key=output_key)
                break
            except Exception:
                time.sleep(1)

        # Download processed image
        buffer = BytesIO()
        s3.download_fileobj(OUTPUT_BUCKET, output_key, buffer)
        buffer.seek(0)

        return send_file(buffer, mimetype="image/jpeg")

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
