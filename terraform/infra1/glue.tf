resource "aws_glue_job" "pgyr_job" {
  name     = "ter-bronze-to-silver-job"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    script_location = "s3://ter-bronze-data-sahil/scripts/bronze_to_silver.py"
    python_version  = "3"
  }

  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 2

  default_arguments = {
    "--job-language" = "python"
  }
}

