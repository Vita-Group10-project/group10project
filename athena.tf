resource "aws_athena_workgroup" "ter_wg" {
  name = "ter-workgroup"

  configuration {
    result_configuration {
      output_location = "s3://ter-gold-data-sahil/athena-results/"
    }
  }
}

