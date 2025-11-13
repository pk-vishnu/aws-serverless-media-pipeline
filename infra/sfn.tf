# Step Function Definition
resource "aws_sfn_state_machine" "image_processing_workflow" {
  name     = "ImageProcessingWorkflow"
  role_arn = aws_iam_role.sfn_exec_role.arn

  # This is the Amazon States Language definition
  definition = jsonencode({
    "Comment" : "Orchestrates image processing and analysis",
    "StartAt" : "GetS3EventInfo",
    "States" : {
      "GetS3EventInfo" : {
        "Type" : "Pass",
        "Parameters" : {
          # Extract the bucket and key from the EventBridge event
          "src_bucket.$" : "$.detail.bucket.name",
          "src_key.$" : "$.detail.object.key",
          # Re-create the original S3 event format for the processor lambda
          # This avoids having to change image_processor.py
          "original_s3_event" : {
            "Records" : [
              {
                "s3" : {
                  "bucket" : { "name.$" : "$.detail.bucket.name" },
                  "object" : { "key.$" : "$.detail.object.key" }
                }
              }
            ]
          }
        },
        "Next" : "ParallelProcessing"
      },
      "ParallelProcessing" : {
        "Type" : "Parallel",
        "Next" : "AnalyzeProcessedImage",
        "Branches" : [
          # --- Branch A: Process the Image ---
          {
            "StartAt" : "ProcessImage",
            "States" : {
              "ProcessImage" : {
                "Type" : "Task",
                "Resource" : "arn:aws:states:::lambda:invoke",
                "Parameters" : {
                  "FunctionName" : aws_lambda_function.image_processor.function_name,
                  "Payload.$" : "$.original_s3_event"
                },
                "End" : true
              }
            }
          },
          # --- Branch B: Analyze the ORIGINAL Image ---
          {
            "StartAt" : "AnalyzeOriginalImage",
            "States" : {
              "AnalyzeOriginalImage" : {
                "Type" : "Task",
                "Resource" : "arn:aws:states:::lambda:invoke",
                "Parameters" : {
                  "FunctionName" : aws_lambda_function.image_analyzer.function_name,
                  "Payload" : {
                    "source_bucket.$" : "$.src_bucket",
                    "source_key.$" : "$.src_key",
                    "analysis_key.$" : "States.Format('analysis/{}_original_hist.png', $.src_key)",
                    "title" : "Original Image Histogram"
                  }
                },
                "End" : true
              }
            }
          }
        ]
      },
      # --- Step 3: Analyze the PROCESSED Image ---
      "AnalyzeProcessedImage" : {
        "Type" : "Task",
        "Resource" : "arn:aws:states:::lambda:invoke",
        "Parameters" : {
          "FunctionName" : aws_lambda_function.image_analyzer.function_name,
          "Payload" : {
            "source_bucket" : aws_s3_bucket.output_bucket.bucket,
            "source_key.$" : "$[0].Payload.output",
            "analysis_key.$" : "States.Format('analysis/{}_processed_hist.png', $[0].Payload.output)",
            "title" : "Processed Image Histogram"
          }
        },
        "End" : true
      }
    }
  })

  tags = {
    Name = "sfn-image-workflow"
  }
}

# S3 TRIGGER (via EventBridge)
# First, an EventBridge rule to catch the S3 event
resource "aws_cloudwatch_event_rule" "s3_upload_rule" {
  name        = "s3-upload-to-sfn-rule"
  description = "Trigger Step Function on S3 upload"

  event_pattern = jsonencode({
    "source" : ["aws.s3"],
    "detail-type" : ["Object Created"],
    "detail" : {
      "bucket" : {
        "name" : [aws_s3_bucket.input_bucket.bucket]
      }
    }
  })
}

# Then, a target to link the rule to the Step Function
resource "aws_cloudwatch_event_target" "sfn_target" {
  rule     = aws_cloudwatch_event_rule.s3_upload_rule.name
  arn      = aws_sfn_state_machine.image_processing_workflow.id
  role_arn = aws_iam_role.eventbridge_to_sfn_role.arn
}
