resource "aws_s3_bucket" "raw_bucket" {
  bucket = "my-project-raw-data"
}

resource "aws_s3_bucket" "clean_bucket" {
  bucket = "my-project-clean-data"
}

resource "aws_s3_bucket" "athena_results" {
  bucket = "my-project-athena-results"
}
