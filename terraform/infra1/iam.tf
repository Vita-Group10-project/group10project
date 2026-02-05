############################################################
# GLUE IAM ROLE
############################################################
resource "aws_iam_role" "glue_role" {
  name = "ter-glue-etl-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "glue.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

############################################################
# AWS MANAGED GLUE POLICY
############################################################
resource "aws_iam_role_policy_attachment" "glue_policy" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

############################################################
# ⭐ DYNAMIC S3 ACCESS (NO HARDCODING)
############################################################
resource "aws_iam_role_policy" "glue_s3_access" {
  name = "ter-glue-s3-access"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [

      #########################################
      # OBJECT LEVEL (read/write/delete)
      #########################################
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        Resource = [
          "${data.aws_s3_bucket.bronze.arn}/*",
          "${data.aws_s3_bucket.silver.arn}/*",
          "${data.aws_s3_bucket.gold.arn}/*"
        ]
      },

      #########################################
      # BUCKET LEVEL (list)
      #########################################
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket"
        ],
        Resource = [
          data.aws_s3_bucket.bronze.arn,
          data.aws_s3_bucket.silver.arn,
          data.aws_s3_bucket.gold.arn
        ]
      }
    ]
  })
}
