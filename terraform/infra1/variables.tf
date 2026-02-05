#########################################################
# BUCKET NAMES (passed from GitHub Actions)
#########################################################

variable "bronze_bucket_name" {
  description = "Raw/Bronze bucket name"
  type        = string
}

variable "silver_bucket_name" {
  description = "Silver/Enriched bucket name"
  type        = string
}

variable "gold_bucket_name" {
  description = "Gold/Reporting bucket name"
  type        = string
}


#########################################################
# CMS SOURCE FILE
#########################################################

variable "cms_url" {
  description = "CMS download URL"
  type        = string
}
