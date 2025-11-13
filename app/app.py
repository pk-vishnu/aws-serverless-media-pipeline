import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

import s3_utils

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

INPUT_BUCKET = os.getenv("INPUT_BUCKET")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")

SUPPORTED_OPERATIONS = {
    "grayscale": "Grayscale",
    "thumbnail": "Thumbnail (200px)",
    "blur": "Apply Blur",
    "edges": "Find Edges",
}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part selected.", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected.", "error")
            return redirect(request.url)

        # Get a list of all checked operations
        operations_list = request.form.getlist("operations")

        if not operations_list:
            flash("Please select at least one operation.", "error")
            return redirect(request.url)

        # Validate operations against our supported list
        valid_operations = []
        for op in operations_list:
            if op in SUPPORTED_OPERATIONS:
                valid_operations.append(op)

        if not valid_operations:
            flash("No valid operations selected.", "error")
            return redirect(request.url)

        if file:
            # Generate a unique key for S3
            unique_key = s3_utils.get_unique_key(file.filename)

            # join the list into a comma-separated string ---
            operations_string = ",".join(valid_operations)

            # Metadata to pass to Lambda
            metadata = {"operations": operations_string}

            # 1. Upload to the INPUT bucket
            success = s3_utils.upload_to_s3(file, INPUT_BUCKET, unique_key, metadata)

            if not success:
                flash("There was an error uploading your file.", "error")
                return redirect(request.url)

            # 2. Upload successful, now wait for processing
            processed_key = f"processed/{unique_key}"

            try:
                # 3. Wait for the Lambda to create the processed file
                s3_utils.wait_for_object(OUTPUT_BUCKET, processed_key)

                # 4. Get presigned URLs for both images
                original_url = s3_utils.get_presigned_url(INPUT_BUCKET, unique_key)
                processed_url = s3_utils.get_presigned_url(OUTPUT_BUCKET, processed_key)

                if not original_url or not processed_url:
                    flash("Error generating links to your images.", "error")
                    return redirect(url_for("index"))

                # 5. Re-render the same page with results

                # Get display names for the template
                display_names = [
                    SUPPORTED_OPERATIONS.get(op, op) for op in valid_operations
                ]
                operation_name_str = " + ".join(display_names)

                return render_template(
                    "index.html",
                    operations=SUPPORTED_OPERATIONS,
                    original_url=original_url,
                    processed_url=processed_url,
                    operation_name=operation_name_str,
                )

            except TimeoutError:
                flash(
                    f"Image processing timed out. Please try again. (Waited for: {processed_key})",
                    "error",
                )
                return redirect(url_for("index"))
            except Exception as e:
                flash(f"An unexpected error occurred: {e}", "error")
                return redirect(url_for("index"))

    return render_template("index.html", operations=SUPPORTED_OPERATIONS)


if __name__ == "__main__":
    if not INPUT_BUCKET or not OUTPUT_BUCKET:
        print(
            "Error: INPUT_BUCKET and OUTPUT_BUCKET environment variables are not set."
        )
    else:
        print(f"Image Lab running.")
        print(f"Input Bucket: {INPUT_BUCKET}")
        print(f"Output Bucket: {OUTPUT_BUCKET}")
        app.run(debug=True, host="0.0.0.0", port=5000)
