############################################################
# BRONZE (RAW INGESTION BUCKET → CREATED BY TERRAFORM)
############################################################
resource "aws_s3_bucket" "bronze" {
  bucket = "cms-open-payment-raw-zone"

  force_destroy = true

  tags = {
    Layer = "bronze"
    Name  = "raw-zone"
  }
}

############################################################
# SILVER (ENRICHED → ALREADY EXISTS)
############################################################
data "aws_s3_bucket" "silver" {
  bucket = "enriched-zone-00"
}

############################################################
# GOLD (ATHENA RESULTS → ALREADY EXISTS)
############################################################
data "aws_s3_bucket" "gold" {
  bucket = "reporting-zone-00"
}

############################################################
# OUTPUTS (OPTIONAL BUT USEFUL)
############################################################
output "bronze_bucket" {
  value = aws_s3_bucket.bronze.bucket
}

output "silver_bucket" {
  value = data.aws_s3_bucket.silver.bucket
}

output "gold_bucket" {
  value = data.aws_s3_bucket.gold.bucket
}
