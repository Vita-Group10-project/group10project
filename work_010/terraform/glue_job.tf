resource "aws_glue_job" "etl_job" {
  name     = "raw-to-clean-job"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://my-project-raw-data/scripts/glue_job.py"
  }

  glue_version = "4.0"
  max_capacity = 2
}
