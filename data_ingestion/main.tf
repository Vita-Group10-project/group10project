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

# =========================================================
# VARIABLES
# =========================================================
variable "project_name" {
  type    = string
  default = "cms-ec2-download"
}

variable "key_name" {
  type    = string
  default = "vm_stream"
}

variable "instance_type" {
  type = string
  default = "c7i-flex.large"
}

variable "bucket_name" {
  type    = string
  default = "ter-dump-sahil"
}

variable "cms_url" {
  type    = string
  default = "https://download.cms.gov/openpayments/PGYR2024_P01232026_01102026/OP_DTL_GNRL_PGYR2024_P01232026_01102026.csv"
}

# =========================================================
# (OPTIONAL) CREATE S3 BUCKET (Enable if bucket not exists)
# Uncomment this block only if bucket doesn't exist
# =========================================================
# resource "aws_s3_bucket" "dump_bucket" {
#   bucket        = var.bucket_name
#   force_destroy = true
#
#   tags = {
#     Name = "${var.project_name}-bucket"
#   }
# }

# =========================================================
# VPC + SUBNET + IGW + ROUTE TABLE
# =========================================================
resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

# =========================================================
# SECURITY GROUP
# =========================================================
resource "aws_security_group" "ec2_sg" {
  name        = "${var.project_name}-sg"
  description = "Allow SSH + outbound internet"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # ⚠️ for learning only
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

# =========================================================
# IAM ROLE + POLICY (S3 Multipart Upload Allowed)
# =========================================================
resource "aws_iam_policy" "s3_policy" {
  name        = "${var.project_name}-s3-policy"
  description = "Allow EC2 to upload CMS file to S3 + terminate itself"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [

      # ✅ Allow bucket-level actions
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::${var.bucket_name}"
        ]
      },

      # ✅ Allow object upload including multipart
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",

          "s3:AbortMultipartUpload",
          "s3:CreateMultipartUpload",
          "s3:UploadPart",
          "s3:CompleteMultipartUpload",
          "s3:ListMultipartUploadParts"
        ]
        Resource = [
          "arn:aws:s3:::${var.bucket_name}/*"
        ]
      },

      # ✅ Allow EC2 to terminate itself after success
      {
        Effect = "Allow"
        Action = [
          "ec2:TerminateInstances",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      }
    ]
  })
}
# =========================================================
# IAM ROLE (EC2 assumes this)
# =========================================================
resource "aws_iam_role" "EC2_role" {
  name = "${var.project_name}-EC2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}


# =========================================================
# ATTACH YOUR POLICY TO ROLE
# =========================================================
resource "aws_iam_role_policy_attachment" "ec2_attach_policy" {
  role       = aws_iam_role.EC2_role.name
  policy_arn = aws_iam_policy.s3_policy.arn
}


# =========================================================
# ⭐ REQUIRED → INSTANCE PROFILE (EC2 NEEDS THIS)
# =========================================================
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.EC2_role.name
}


# =========================================================
# AMI (AMAZON LINUX 2)
# =========================================================
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}
# =========================================================
# EC2 INSTANCE + USER DATA (AUTO DOWNLOAD + UPLOAD)
# =========================================================
resource "aws_instance" "cms_ec2" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public_subnet.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  key_name               = var.key_name

  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    set -e

    yum update -y
    yum install -y python3
    python3 -m ensurepip --upgrade || true
    python3 -m pip install --upgrade pip
    python3 -m pip install boto3 requests awscli

    mkdir -p /home/ec2-user/cms_job
    cd /home/ec2-user/cms_job

    cat << 'PY' > cms_download.py
    import boto3
    import requests
    from datetime import datetime

    url = "${var.cms_url}"
    bucket = "${var.bucket_name}"

    today = datetime.today().strftime("%Y-%m-%d")
    key = f"cms/raw/{today}/PGYR2024_P01232026_01102026.zip"

    s3 = boto3.client("s3")

    print("✅ Downloading CMS file and uploading to S3....")
    response = requests.get(url, stream=True, timeout=1800)
    response.raise_for_status()

    s3.upload_fileobj(response.raw, bucket, key)

    print(f"✅ Uploaded to s3://{bucket}/{key}")
    PY

    chown -R ec2-user:ec2-user /home/ec2-user/cms_job

    # ✅ Run ingestion job (foreground)
    python3 /home/ec2-user/cms_job/cms_download.py > /home/ec2-user/cms_job/cms_job.log 2>&1

    # ✅ Terminate instance after success
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    aws ec2 terminate-instances --region us-east-1 --instance-ids $INSTANCE_ID
  EOF

  tags = {
    Name = "${var.project_name}-ec2"
  }
}



# =========================================================
# OUTPUTS
# =========================================================
output "ec2_public_ip" {
  value = aws_instance.cms_ec2.public_ip
}

output "ssh_command" {
  value = "ssh -i vm_stream.pem ec2-user@${aws_instance.cms_ec2.public_ip}"
}
