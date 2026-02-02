terraform import aws_s3_bucket.bronze ter-raw-zone-sahil
terraform import aws_s3_bucket.silver ter-enriched-zone-sahil
terraform import aws_s3_bucket.gold ter-reorting-zone-sahil
terraform import aws_glue_crawler.silver_crawler ter-silver-crawler
terraform import aws_glue_catalog_database.silver_db ter_silver_db


############################
# GLUE DATABASE
############################
resource "aws_glue_catalog_database" "silver_db" {
  name = "ter_silver_db"

  lifecycle {
    prevent_destroy = true
  }
}
