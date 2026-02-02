resource "aws_glue_catalog_database" "silver_db" {
  name = "ter_silver_db"
}

resource "aws_glue_crawler" "silver_crawler" {
  name          = "ter-silver-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.silver_db.name

  s3_target {
    path = "s3://ter-silver-data-sahil/output/"
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

  # ✅ THIS IS THE IMPORTANT PART
  lifecycle {
    prevent_destroy = false
    create_before_destroy = false
  }
}
