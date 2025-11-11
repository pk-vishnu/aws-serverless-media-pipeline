variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = ""
}

variable "aws_profile" {
  description = "Optional AWS CLI profile name (leave empty to use env creds)"
  type        = string
  default     = ""
}

variable "input_bucket_prefix" {
  description = "Prefix for input S3 bucket name"
  type        = string
  default     = "media-input-"
}

variable "output_bucket_prefix" {
  description = "Prefix for output S3 bucket name"
  type        = string
  default     = "media-output-"
}
