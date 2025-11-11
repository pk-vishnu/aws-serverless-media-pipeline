resource "aws_lambda_function" "image_processor" {
  function_name = "media_image_processor"
  runtime       = "python3.11"
  handler       = "image_processor.lambda_handler"
  role          = aws_iam_role.lambda_exec_role.arn
  filename         = "${path.module}/../build/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../build/lambda.zip")
  timeout       = 30

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

# Allow S3 to invoke the Lambda
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.image_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.input_bucket.arn
}

# S3 event notification trigger
resource "aws_s3_bucket_notification" "input_trigger" {
  bucket = aws_s3_bucket.input_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.image_processor.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [
    aws_lambda_permission.allow_s3_invoke,
    aws_lambda_function.image_processor
  ]
}
