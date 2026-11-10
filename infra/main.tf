terraform {
  required_version = ">= 1.5.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
}
provider "aws" { region = var.aws_region }
provider "aws" { alias = "use1"; region = "us-east-1" }
variable "aws_region" { type = string; default = "us-east-1" }
variable "domain_name" { type = string; description = "Exact hostname (e.g. csce412example.com)" }
variable "hosted_zone_name" { type = string; description = "Existing Route53 zone name (e.g. example.com)" }
variable "bucket_name" { type = string; description = "Globally unique S3 bucket name" }
data "aws_route53_zone" "zone" { name = var.hosted_zone_name; private_zone = false }
resource "aws_s3_bucket" "site" { bucket = var.bucket_name }
resource "aws_s3_bucket_public_access_block" "private" {
  bucket = aws_s3_bucket.site.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_ownership_controls" "owned" {
  bucket = aws_s3_bucket.site.id
  rule { object_ownership = "BucketOwnerEnforced" }
}
resource "aws_cloudfront_origin_access_control" "oac" {
  name = "${var.bucket_name}-oac"
  description = "Private S3 access"
  origin_access_control_origin_type = "s3"
  signing_behavior = "always"
  signing_protocol = "sigv4"
}
resource "aws_acm_certificate" "cert" {
  provider = aws.use1
  domain_name = var.domain_name
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}
resource "aws_route53_record" "cert_validation" {
  for_each = { for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
    name = dvo.resource_record_name
    record = dvo.resource_record_value
    type = dvo.resource_record_type
  } }
  zone_id = data.aws_route53_zone.zone.zone_id
  name = each.value.name
  type = each.value.type
  ttl = 60
  records = [each.value.record]
  allow_overwrite = true
}
resource "aws_acm_certificate_validation" "cert" {
  provider = aws.use1
  certificate_arn = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}
resource "aws_cloudfront_distribution" "cdn" {
  enabled = true
  is_ipv6_enabled = true
  default_root_object = "index.html"
  aliases = [var.domain_name]
  origin {
    domain_name = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id = "s3-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }
  default_cache_behavior {
    allowed_methods = ["GET", "HEAD"]
    cached_methods = ["GET", "HEAD"]
    target_origin_id = "s3-site"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
    min_ttl = 0
    default_ttl = 30
    max_ttl = 300
    compress = true
  }
  restrictions { geo_restriction { restriction_type = "none" } }
  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate_validation.cert.certificate_arn
    ssl_support_method = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
  price_class = "PriceClass_100"
}
resource "aws_s3_bucket_policy" "cloudfront_only" {
  bucket = aws_s3_bucket.site.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Sid = "AllowCloudFrontServicePrincipalReadOnly", Effect = "Allow",
    Principal = { Service = "cloudfront.amazonaws.com" }, Action = "s3:GetObject",
    Resource = "${aws_s3_bucket.site.arn}/*",
    Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.cdn.arn } }
  }] })
  depends_on = [aws_s3_bucket_public_access_block.private]
}
resource "aws_route53_record" "domain_a" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name = var.domain_name
  type = "A"
  alias { name = aws_cloudfront_distribution.cdn.domain_name
          zone_id = aws_cloudfront_distribution.cdn.hosted_zone_id
          evaluate_target_health = false }
}
resource "aws_route53_record" "domain_aaaa" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name = var.domain_name
  type = "AAAA"
  alias { name = aws_cloudfront_distribution.cdn.domain_name
          zone_id = aws_cloudfront_distribution.cdn.hosted_zone_id
          evaluate_target_health = false }
}
output "website_url" { value = "https://${var.domain_name}" }
output "bucket_name" { value = aws_s3_bucket.site.id }
output "distribution_id" { value = aws_cloudfront_distribution.cdn.id }
