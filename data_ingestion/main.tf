############################################################
# TERRAFORM + PROVIDER
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
# VARIABLES (passed from GitHub Actions)
############################################################
variable "bronze_bucket_name" { type = string }
variable "silver_bucket_name" { type = string }
variable "gold_bucket_name"   { type = string }
variable "cms_url"            { type = string }

variable "instance_type" {
  type    = string
  default = "t3.micro"   # ✅ Free tier safe
}

############################################################
# USE DEFAULT VPC (avoid VPC limits)
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
# SECURITY GROUP (OUTBOUND ONLY)
############################################################
resource "aws_security_group" "ec2_sg" {
  name_prefix = "cms-ingest-sg-"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

############################################################
# IAM ROLE FOR EC2 (REQUIRED FOR S3 UPLOAD)
############################################################
resource "aws_iam_role" "role" {
  name_prefix = "cms-ingest-role-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ec2.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

############################################################
# S3 + TERMINATE POLICY
############################################################
resource "aws_iam_policy" "policy" {
  name_prefix = "cms-ingest-policy-"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [

      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ],
        Resource = [
          "arn:aws:s3:::${var.bronze_bucket_name}",
          "arn:aws:s3:::${var.bronze_bucket_name}/*"
        ]
      },

      {
        Effect = "Allow",
        Action = [
          "ec2:TerminateInstances",
          "ec2:DescribeInstances"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.policy.arn
}

resource "aws_iam_instance_profile" "profile" {
  name_prefix = "cms-profile-"
  role        = aws_iam_role.role.name
}

############################################################
# AMAZON LINUX AMI
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

print("Uploaded:", f"s3://{bucket}/{key}")
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
