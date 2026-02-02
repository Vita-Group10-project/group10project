############################
# BRONZE BUCKET
############################
resource "aws_s3_bucket" "bronze" {
  bucket = "ter-raw-zone-sahil"

  lifecycle {
    prevent_destroy = true
  }
}

############################
# SILVER BUCKET
############################
resource "aws_s3_bucket" "silver" {
  bucket = "ter-enriched-zone-sahil"

  lifecycle {
    prevent_destroy = true
  }
}

############################
# GOLD BUCKET
############################
resource "aws_s3_bucket" "gold" {
  bucket = "ter-reorting-zone-sahil"

  lifecycle {
    prevent_destroy = true
  }
}

############################
# CRAWLER FOLDER (IMPORTANT)
############################
resource "aws_s3_object" "crawler_prefix" {
  bucket  = aws_s3_bucket.silver.bucket
  key     = "output/"
  content = ""
}
