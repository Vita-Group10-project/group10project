resource "aws_athena_workgroup" "analytics" {
  name = "analytics-wg"

  configuration {
    result_configuration {
      output_location = "s3://my-project-athena-results/"
    }
  }
}
