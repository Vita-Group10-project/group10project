############################################################
# S3 BUCKETS (EXISTING → PASSED FROM CICD)
############################################################

variable "bronze_bucket_name" {
  description = "Raw/Bronze ingestion bucket (existing)"
  type        = string
}

variable "silver_bucket_name" {
  description = "Enriched/Silver bucket (existing)"
  type        = string
}

variable "gold_bucket_name" {
  description = "Reporting/Gold bucket (existing)"
  type        = string
}

############################################################
# INGEST CONFIG
############################################################

variable "cms_url" {
  description = "Public CMS download URL"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for ingestion job"
  type        = string
  default     = "t3.micro"   # safe + cheap
}

############################################################
# OPTIONAL PROJECT TAGGING
############################################################

variable "project_name" {
  description = "Project name prefix for tagging"
  type        = string
  default     = "cms-ingestion"
}

############################################################
# REGION (optional override)
############################################################

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
