resource "aws_s3_bucket" "input_bucket" {
  bucket_prefix = var.input_bucket_prefix
  acl           = "private"

  versioning {
    enabled = true
  }

  tags = {
    Name = "media-input"
    Env  = "dev"
  }
}

resource "aws_s3_bucket" "output_bucket" {
  bucket_prefix = var.output_bucket_prefix
  acl           = "private"

  versioning {
    enabled = true
  }

  tags = {
    Name = "media-output"
    Env  = "dev"
  }
}
