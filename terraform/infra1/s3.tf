resource "aws_s3_bucket" "bronze" { 
bucket = "ter-raw-zone-sahil" lifecycle 
{ prevent_destroy = true } }


data "aws_s3_bucket" "silver" {
  bucket = "enriched-zone-00"
}

data "aws_s3_bucket" "gold" {
  bucket = "reporting-zone-00"
}
