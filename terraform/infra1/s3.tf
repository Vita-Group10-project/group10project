############################################################
# EXISTING BUCKETS ONLY (NO CREATION)
############################################################

data "aws_s3_bucket" "bronze" {
  bucket = var.bronze_bucket_name
}

data "aws_s3_bucket" "silver" {
  bucket = var.silver_bucket_name
}

data "aws_s3_bucket" "gold" {
  bucket = var.gold_bucket_name
}

############################################################
# OUTPUTS (optional)
############################################################
output "bronze_bucket" {
  value = data.aws_s3_bucket.bronze.bucket
}

output "silver_bucket" {
  value = data.aws_s3_bucket.silver.bucket
}

output "gold_bucket" {
  value = data.aws_s3_bucket.gold.bucket
}
