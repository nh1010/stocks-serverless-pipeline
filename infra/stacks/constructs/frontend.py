"""Frontend construct: S3 bucket + CloudFront distribution + BucketDeployment."""

import os

import aws_cdk as cdk
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3deploy
import aws_cdk.aws_cloudfront as cloudfront
import aws_cdk.aws_cloudfront_origins as origins
from constructs import Construct

FRONTEND_DIST = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "frontend", "dist"
)


class Frontend(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        api_url: str,
    ) -> None:
        super().__init__(scope, id)

        bucket = s3.Bucket(
            self,
            "SiteBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(0),
                ),
            ],
        )

        s3deploy.BucketDeployment(
            self,
            "DeploySite",
            sources=[s3deploy.Source.asset(FRONTEND_DIST)],
            destination_bucket=bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
        )

        self.distribution_url = (
            f"https://{self.distribution.distribution_domain_name}"
        )
