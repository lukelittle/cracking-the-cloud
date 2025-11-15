terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "random_string" "suffix" {
  length  = 5
  special = false
  upper   = false
}

# --- S3 Bucket for Frontend ---
resource "aws_s3_bucket" "website_bucket" {
  bucket = "cracking-the-cloud-survey-${random_string.suffix.result}"
}

resource "aws_s3_bucket_website_configuration" "website_config" {
  bucket = aws_s3_bucket.website_bucket.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "public_access" {
  bucket = aws_s3_bucket.website_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "cracking-the-cloud-survey-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_s3_bucket_policy" "bucket_policy" {
  bucket = aws_s3_bucket.website_bucket.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = {
        Service = "cloudfront.amazonaws.com"
      },
      Action    = "s3:GetObject",
      Resource  = "${aws_s3_bucket.website_bucket.arn}/*",
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.s3_distribution.arn
        }
      }
    }]
  })
}

resource "aws_s3_object" "website_files" {
  for_each = fileset("../website/", "*.{html,css}")
  bucket   = aws_s3_bucket.website_bucket.id
  key      = each.value
  source   = "../website/${each.value}"
  etag     = filemd5("../website/${each.value}")
  content_type = each.key == "style.css" ? "text/css" : "text/html"
}

resource "aws_s3_object" "main_js" {
  bucket   = aws_s3_bucket.website_bucket.id
  key      = "main.js"
  content  = templatefile("../website/main.js", {
    API_URL = aws_apigatewayv2_stage.default_stage.invoke_url
  })
  etag     = md5(templatefile("../website/main.js", {
    API_URL = aws_apigatewayv2_stage.default_stage.invoke_url
  }))
  content_type = "application/javascript"
}

# --- CloudFront Distribution ---
resource "aws_cloudfront_distribution" "s3_distribution" {
  origin {
    domain_name              = aws_s3_bucket.website_bucket.bucket_regional_domain_name
    origin_id                = aws_s3_bucket.website_bucket.id
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = aws_s3_bucket.website_bucket.id

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

# --- DynamoDB Table ---
resource "aws_dynamodb_table" "survey_table" {
  name           = "CrackingTheCloudSurvey"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# --- IAM Role for Lambda ---
resource "aws_iam_role" "lambda_exec_role" {
  name = "CrackingTheCloudLambdaRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_basic" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_policy_dynamodb" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" # For simplicity
}

# --- Lambda Functions ---
data "archive_file" "vote_zip" {
  type        = "zip"
  source_file = "../backend/vote.py"
  output_path = "vote.zip"
}

resource "aws_lambda_function" "vote_function" {
  function_name = "CrackingTheCloudVote"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "vote.handler"
  runtime       = "python3.9"
  filename      = data.archive_file.vote_zip.output_path
  source_code_hash = data.archive_file.vote_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.survey_table.name
    }
  }
}

data "archive_file" "results_zip" {
  type        = "zip"
  source_file = "../backend/results.py"
  output_path = "results.zip"
}

resource "aws_lambda_function" "results_function" {
  function_name = "CrackingTheCloudResults"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "results.handler"
  runtime       = "python3.9"
  filename      = data.archive_file.results_zip.output_path
  source_code_hash = data.archive_file.results_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.survey_table.name
    }
  }
}

data "archive_file" "reset_zip" {
  type        = "zip"
  source_file = "../backend/reset.py"
  output_path = "reset.zip"
}

resource "aws_lambda_function" "reset_function" {
  function_name = "CrackingTheCloudReset"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "reset.handler"
  runtime       = "python3.9"
  filename      = data.archive_file.reset_zip.output_path
  source_code_hash = data.archive_file.reset_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.survey_table.name
    }
  }
}

# --- API Gateway ---
resource "aws_apigatewayv2_api" "survey_api" {
  name          = "CrackingTheCloudSurveyAPI"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_integration" "vote_integration" {
  api_id           = aws_apigatewayv2_api.survey_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.vote_function.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "results_integration" {
  api_id           = aws_apigatewayv2_api.survey_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.results_function.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "reset_integration" {
  api_id           = aws_apigatewayv2_api.survey_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.reset_function.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "vote_route" {
  api_id    = aws_apigatewayv2_api.survey_api.id
  route_key = "POST /vote"
  target    = "integrations/${aws_apigatewayv2_integration.vote_integration.id}"
}

resource "aws_apigatewayv2_route" "results_route" {
  api_id    = aws_apigatewayv2_api.survey_api.id
  route_key = "GET /results"
  target    = "integrations/${aws_apigatewayv2_integration.results_integration.id}"
}

resource "aws_apigatewayv2_route" "reset_route" {
  api_id    = aws_apigatewayv2_api.survey_api.id
  route_key = "POST /reset"
  target    = "integrations/${aws_apigatewayv2_integration.reset_integration.id}"
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.survey_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway_permission_vote" {
  statement_id  = "AllowAPIGatewayToInvokeVote"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.vote_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.survey_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_permission_results" {
  statement_id  = "AllowAPIGatewayToInvokeResults"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.results_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.survey_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_permission_reset" {
  statement_id  = "AllowAPIGatewayToInvokeReset"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reset_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.survey_api.execution_arn}/*/*"
}
