############################################################
# EXISTING BUCKETS ONLY (NO CREATION)
############################################################

data "aws_s3_bucket" "bronze" {
  bucket = var.raw-zone-00
}

data "aws_s3_bucket" "silver" {
  bucket = var.enriched-zone-00
}

data "aws_s3_bucket" "gold" {
  bucket = var.reporting-zone-00
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
