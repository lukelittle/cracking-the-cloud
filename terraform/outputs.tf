output "cloudfront_domain" {
  description = "The domain name of the CloudFront distribution."
  value       = "https://${aws_cloudfront_distribution.s3_distribution.domain_name}"
}

output "api_endpoint" {
  description = "The invoke URL for the API Gateway."
  value       = aws_apigatewayv2_stage.default_stage.invoke_url
}
