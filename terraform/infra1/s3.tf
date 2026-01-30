resource "aws_s3_bucket" "bronze" {
  bucket = "ter-bronze-data-sahil"
}

resource "aws_s3_bucket" "silver" {
  bucket = "ter-silver-data-sahil"
}

resource "aws_s3_bucket" "gold" {
  bucket = "ter-gold-data-sahil"
}

