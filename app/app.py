import json
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
    "enhance": "Enhance Contrast (+1.5)",
    "sepia": "Sepia Tone",
    "crop_pad": "Crop to 9:16",
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

        operations_order = request.form.get("operations_order")

        try:
            ordered_ops = json.loads(operations_order)
        except:
            ordered_ops = []

        # Validate operations against our supported list
        valid_operations = [op for op in ordered_ops if op in SUPPORTED_OPERATIONS]

        if not valid_operations:
            flash("No valid operations selected.", "error")
            return redirect(request.url)

        if file:
            # Generate a unique key for S3
            unique_key = s3_utils.get_unique_key(file.filename)
            base_name, extension = os.path.splitext(unique_key)

            # join the list into a comma-separated string ---
            operations_string = ",".join(valid_operations)

            # Metadata to pass to Lambda
            metadata = {"operations": operations_string}

            # Upload to the INPUT bucket
            success = s3_utils.upload_to_s3(file, INPUT_BUCKET, unique_key, metadata)

            if not success:
                flash("There was an error uploading your file.", "error")
                return redirect(request.url)

            # 2. Upload successful, now wait for processing
            processed_key = f"processed/{base_name}_combined{extension}"
            original_analysis_key = f"analysis/{unique_key}_original_hist.png"
            processed_analysis_key = f"analysis/{processed_key}_processed_hist.png"

            try:
                s3_utils.wait_for_object(OUTPUT_BUCKET, processed_key)
                s3_utils.wait_for_object(OUTPUT_BUCKET, original_analysis_key)
                s3_utils.wait_for_object(OUTPUT_BUCKET, processed_analysis_key)

                original_url = s3_utils.get_presigned_url(INPUT_BUCKET, unique_key)
                processed_url = s3_utils.get_presigned_url(OUTPUT_BUCKET, processed_key)
                original_analysis_url = s3_utils.get_presigned_url(
                    OUTPUT_BUCKET, original_analysis_key
                )
                processed_analysis_url = s3_utils.get_presigned_url(
                    OUTPUT_BUCKET, processed_analysis_key
                )

                if not all(
                    [
                        original_url,
                        processed_url,
                        original_analysis_url,
                        processed_analysis_url,
                    ]
                ):
                    flash("Error generating links to your images.", "error")
                    return redirect(url_for("index"))

                # Get URLs for independent files
                independent_urls = []
                for op in valid_operations:
                    ind_key = f"processed/{base_name}_{op}{extension}"
                    ind_url = s3_utils.get_presigned_url(OUTPUT_BUCKET, ind_key)
                    if ind_url:
                        independent_urls.append(
                            {"name": SUPPORTED_OPERATIONS.get(op, op), "url": ind_url}
                        )

                # Re-render the same page with results
                display_names = [
                    SUPPORTED_OPERATIONS.get(op, op) for op in valid_operations
                ]
                operation_name_str = " + ".join(display_names)

                return render_template(
                    "index.html",
                    operations=SUPPORTED_OPERATIONS,
                    original_url=original_url,
                    processed_url=processed_url,
                    original_analysis_url=original_analysis_url,
                    processed_analysis_url=processed_analysis_url,
                    operation_name=operation_name_str,
                    independent_urls=independent_urls,
                )

            except TimeoutError:
                flash(
                    f"Image processing timed out. Please try again. (Waited for: {processed_key}, {original_analysis_key}, or {processed_analysis_key})",
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
