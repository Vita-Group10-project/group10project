resource "aws_glue_job" "pgyr_job" {
  name     = var.glue_job_name
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    script_location = var.glue_script_s3_path
    python_version  = "3"
  }

  glue_version      = var.glue_version
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers

  default_arguments = {
    "--job-language" = "python"
  }
}
