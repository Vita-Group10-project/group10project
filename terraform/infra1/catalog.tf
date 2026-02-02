############################
# GLUE CRAWLER
############################
resource "aws_glue_crawler" "silver_crawler" {

  name          = "ter-silver-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.silver_db.name

  s3_target {
    path = "s3://${aws_s3_bucket.silver.bucket}/output/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Tables = {
        AddOrUpdateBehavior = "MergeNewColumns"
      }
    }
  })

  depends_on = [
    aws_s3_object.crawler_prefix
  ]

  lifecycle {
    create_before_destroy = false
  }
}

############################
# GLUE DATABASE
############################
resource "aws_glue_catalog_database" "silver_db" {
  name = "ter_silver_db"

  lifecycle {
    prevent_destroy = true
  }
}
