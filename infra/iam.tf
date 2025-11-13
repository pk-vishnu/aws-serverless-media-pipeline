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

# This role allows the Step Function to invoke Lambda functions
resource "aws_iam_role" "sfn_exec_role" {
  name = "sfn-lambda-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "states.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { Name = "sfn-execution-role" }
}

resource "aws_iam_policy" "sfn_lambda_policy" {
  name = "sfn-lambda-invoke-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = "lambda:InvokeFunction",
      Resource = [
        aws_lambda_function.image_processor.arn,
        aws_lambda_function.image_analyzer.arn
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "sfn_lambda_attach" {
  role       = aws_iam_role.sfn_exec_role.name
  policy_arn = aws_iam_policy.sfn_lambda_policy.arn
}

# This role allows EventBridge to start the Step Function
resource "aws_iam_role" "eventbridge_to_sfn_role" {
  name = "eventbridge-to-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "events.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { Name = "eventbridge-to-sfn-role" }
}

resource "aws_iam_policy" "eventbridge_sfn_policy" {
  name = "eventbridge-sfn-start-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = "states:StartExecution",
      Resource = aws_sfn_state_machine.image_processing_workflow.id
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eventbridge_sfn_attach" {
  role       = aws_iam_role.eventbridge_to_sfn_role.name
  policy_arn = aws_iam_policy.eventbridge_sfn_policy.arn
}
