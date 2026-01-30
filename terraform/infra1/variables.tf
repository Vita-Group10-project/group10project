variable "glue_job_name" {
  type        = string
  description = "AWS Glue job name"
  default     = "ter-bronze-to-silver-job"
}

variable "glue_script_s3_path" {
  type        = string
  description = "S3 path of Glue ETL script"
  default     = "s3://ter-bronze-data-sahil/scripts/bronze_to_silver.py"
}

variable "glue_version" {
  type        = string
  description = "Glue version"
  default     = "4.0"
}

variable "worker_type" {
  type        = string
  description = "Glue worker type"
  default     = "G.1X"
}

variable "number_of_workers" {
  type        = number
  description = "Number of Glue workers"
  default     = 2
}
