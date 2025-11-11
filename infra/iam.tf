
# IAM role that Lambda will assume when running
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_media_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = {
    Name = "lambda-execution-role"
  }
}

# Policy attached to the Lambda role for S3 + CloudWatch access
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "lambda_s3_access"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowS3Access",
        Effect = "Allow",
        Action = ["s3:GetObject", "s3:PutObject"],
        Resource = [
          "${aws_s3_bucket.input_bucket.arn}/*",
          "${aws_s3_bucket.output_bucket.arn}/*"
        ]
      },
      {
        Sid    = "AllowLogging",
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}
