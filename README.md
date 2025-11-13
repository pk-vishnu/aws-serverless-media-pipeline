## AWS Serverless Image Processing

A fully serverless, event-driven pipeline on AWS for orchestrating image processing and analysis workflows. This project uses AWS Step Functions to manage a parallel workflow triggered by S3 uploads via EventBridge.

![image_processing](https://github.com/user-attachments/assets/29779d02-d16f-4eea-9021-cecba7243c74)

---

## Core Features

* **Event-Driven:** The entire pipeline is triggered by an `Object Created` event in an S3 bucket, captured by **EventBridge**.
* **Step Functions Orchestration:** An **AWS Step Functions** state machine defines and manages the workflow, handling parallel execution and sequencing.
* **Parallel Processing:** The state machine simultaneously runs image processing *and* analysis of the original image in parallel branches.
* **Dynamic Operations:** The `image_processor` Lambda reads a list of operations (e.g., `grayscale`, `blur`, `sepia`) from S3 object metadata.
* **Sequential vs. Independent Output:** The processor generates two sets of results:
    1.  A single **combined** image (all operations applied in sequence).
    2.  An **independent** image for each operation, applied to the original.
* **Automated Analysis:** A separate `image_analyser` Lambda generates color histograms for both the original and final processed images, allowing for visual comparison.
* **Modern Web UI:** A **Flask** and **TailwindCSS** frontend provides a clean interface for uploading images, selecting operations, and viewing the 2x2 results grid.

---

## Architecture
<img width="1000" height="600" alt="architecture" src="https://github.com/user-attachments/assets/2fc00ea5-d94b-4727-8975-0f962d71f421" />

The workflow is fully automated from the moment a file is uploaded.

1.  **Upload:** A user selects an image and a chain of operations (e.g., "Grayscale", "Blur") in the Flask web app. The app uploads the image to the **S3 input bucket** with the operations list attached as S3 metadata (e.g., `x-amz-meta-operations: "grayscale,blur"`).
2.  **Trigger:** **EventBridge** detects the `s3:ObjectCreated` event and triggers the **Step Functions** state machine, passing in the event details.
3.  **Orchestration (Start):** The state machine starts and first extracts the bucket and key from the EventBridge event.
4.  **Parallel State:** The workflow splits into two parallel branches:
    * **Branch A (Process):** Invokes the `image_processor` Lambda. This function downloads the image, reads its S3 metadata, and performs all processing. It saves both the *combined* image and all *independent* effect images to the **S3 output bucket**.
    * **Branch B (Analyze Original):** Invokes the `image_analyser` Lambda on the *original* S3 image to generate its color histogram, saving it to the output bucket.
5.  **Sequential State (Analyze Processed):** *After* the parallel step completes, a final task invokes the `image_analyser` Lambda again. This time, it analyzes the *combined processed image* created in Branch A.
6.  **Results:** The web app, which has been waiting for the workflow to complete, retrieves the URLs for all generated files and displays them in the results grid.

---

## Deployment

1.  **Build Lambdas:**
    * Run the `./build.sh` script to create the `.zip` deployment packages for both Lambda functions.
2.  **Deploy Infrastructure:**
    * Navigate to the `infra/` directory.
    * Initialize Terraform: `terraform init`
    * Plan the deployment: `terraform plan`
    * Apply the configuration: `terraform apply`
3.  **Configure Frontend:**
    * Update the `app/` (Flask) configuration with the outputs from Terraform (e.g., the S3 bucket names).
4.  **Run Application:**
    * Install Python dependencies: `pip install -r app/requirements.txt`
    * Run the Flask server: `flask run`
