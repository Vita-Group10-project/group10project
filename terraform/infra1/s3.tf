data "aws_s3_bucket" "bronze" {
  bucket = "cms-open-payment-raw-data "
}

data "aws_s3_bucket" "silver" {
  bucket = "enriched-zone-00"
}

data "aws_s3_bucket" "gold" {
  bucket = "reporting-zone-00"
}
