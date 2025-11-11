# Input S3 bucket
resource "aws_s3_bucket" "input_bucket" {
  bucket_prefix = var.input_bucket_prefix

  tags = {
    Name = "media-input"
    Env  = "dev"
  }
}

# Output S3 bucket
resource "aws_s3_bucket" "output_bucket" {
  bucket_prefix = var.output_bucket_prefix

  tags = {
    Name = "media-output"
    Env  = "dev"
  }
}

resource "aws_s3_bucket_ownership_controls" "input_ownership" {
  bucket = aws_s3_bucket.input_bucket.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_ownership_controls" "output_ownership" {
  bucket = aws_s3_bucket.output_bucket.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Enable versioning for input bucket
resource "aws_s3_bucket_versioning" "input_versioning" {
  bucket = aws_s3_bucket.input_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable versioning for output bucket
resource "aws_s3_bucket_versioning" "output_versioning" {
  bucket = aws_s3_bucket.output_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}
