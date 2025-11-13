resource "aws_lambda_function" "image_processor" {
  function_name    = "media_image_processor"
  runtime          = "python3.11"
  handler          = "image_processor.lambda_handler"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = "${path.module}/../build/processing_lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../build/processing_lambda.zip")
  timeout          = 30

  environment {
    variables = {
      OUTPUT_BUCKET = aws_s3_bucket.output_bucket.bucket
    }
  }

  tags = {
    Name = "lambda-media-processor"
  }
  layers = [
    "arn:aws:lambda:ap-south-1:770693421928:layer:Klayers-p311-Pillow:10"
  ]
}

resource "aws_lambda_function" "image_analyzer" {
  function_name    = "media_image_analyzer"
  runtime          = "python3.11"
  handler          = "image_analyser.lambda_handler"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = "${path.module}/../build/analyzer_lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../build/analyzer_lambda.zip")
  timeout          = 30

  environment {
    variables = {
      OUTPUT_BUCKET = aws_s3_bucket.output_bucket.bucket
    }
  }

  layers = [
    "arn:aws:lambda:ap-south-1:770693421928:layer:Klayers-p311-Pillow:10"
  ]

  tags = {
    Name = "lambda-media-analyzer"
  }
}

