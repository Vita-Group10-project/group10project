############################################################
# PROVIDER
############################################################
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

############################################################
# DEFAULT VPC (NO LIMIT / NO CUSTOM NETWORK NEEDED)
############################################################
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

############################################################
# SECURITY GROUP (OUTBOUND ONLY FOR DOWNLOAD + S3)
############################################################
resource "aws_security_group" "ec2_sg" {
  name_prefix = "cms-ingest-sg-"
  vpc_id      = data.aws_vpc.default.id

  # Only outbound required
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

############################################################
# AMAZON LINUX 2 AMI
############################################################
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*"]
  }
}

############################################################
# EC2 INGESTION INSTANCE
# Downloads CMS file → uploads to Bronze bucket → self-terminate
############################################################
resource "aws_instance" "cms_ingest" {

  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  iam_instance_profile   = aws_iam_instance_profile.profile.name

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  ##########################################################
  # USER DATA SCRIPT
  ##########################################################
  user_data = <<-EOF
#!/bin/bash
set -e

yum install -y python3 awscli
pip3 install boto3 requests

cat << 'PY' > /tmp/ingest.py
import requests, boto3
from datetime import datetime

url = "${var.cms_url}"
bucket = "${var.bronze_bucket_name}"

today = datetime.today().strftime("%Y-%m-%d")
key = f"cms/raw/{today}/cms.csv"

print("Downloading CMS file...")

r = requests.get(url, stream=True, timeout=1800)
r.raise_for_status()

boto3.client("s3").upload_fileobj(r.raw, bucket, key)

print("Uploaded to:", f"s3://{bucket}/{key}")
PY

python3 /tmp/ingest.py

INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

aws ec2 terminate-instances \
  --region us-east-1 \
  --instance-ids $INSTANCE_ID
EOF

  tags = {
    Name = "cms-ingestion-ec2"
  }
}

############################################################
# OUTPUTS
############################################################
output "bronze_bucket_used" {
  value = var.bronze_bucket_name
}
