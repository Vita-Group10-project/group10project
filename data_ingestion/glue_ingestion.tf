terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

#################################################
# VARIABLES
#################################################
variable "raw_bucket_name" {
  default = "raw-zone-00"
}

variable "script_location" {
  default = "s3://glue-etl-script-00/script/data_ingest.py"
}

variable "glue_role_name" {
  default = "data-ingestion-GlueRole-LkOTIl7IMmuF"
}

variable "cms_url" {
  default = "https://download.cms.gov/openpayments/PGYR2024_P01232026_01102026/OP_DTL_GNRL_PGYR2024_P01232026_01102026.csv"
}

#################################################
# EXISTING IAM ROLE
#################################################
data "aws_iam_role" "existing_glue_role" {
  name = var.glue_role_name
}

#################################################
# GLUE PYTHON SHELL JOB
#################################################
resource "aws_glue_job" "raw_ingestion_job" {
  name     = "raw-zone-00-data-ingestion"
  role_arn = data.aws_iam_role.existing_glue_role.arn

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = var.script_location
  }

  default_arguments = {
    "--RAW_BUCKET"  = var.raw_bucket_name
    "--URL"         = var.cms_url
    "--job-language" = "python"
  }

  max_capacity = 1
  timeout      = 15
}

#################################################
# OUTPUTS
#################################################
output "glue_job_name" {
  value = aws_glue_job.raw_ingestion_job.name
}
