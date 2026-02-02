resource "aws_glue_crawler" "clean_crawler" {
  name          = "clean-data-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = "clean_db"

  s3_target {
    path = "s3://my-project-clean-data/output/"
  }
}
