resource "aws_s3_bucket" "bronze" {
  bucket = "ter-raw-zone-sahil"
}

resource "aws_s3_bucket" "silver" {
  bucket = "ter-enriched-zone-sahil"
}

resource "aws_s3_bucket" "gold" {
  bucket = "ter-reorting-zone-sahil"
}

resource "aws_s3_bucket" "raw" {
  bucket = "ter-dump-sahil"
}

