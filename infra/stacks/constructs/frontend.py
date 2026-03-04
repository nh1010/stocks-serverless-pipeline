from pathlib import Path

from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


class Frontend(Construct):
    def __init__(self, scope: Construct, id: str, *, api_url: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.bucket = s3.Bucket(
            self,
            "SiteBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
            ],
        )

        s3deploy.BucketDeployment(
            self,
            "DeploySite",
            sources=[s3deploy.Source.asset(str(FRONTEND_DIST))],
            destination_bucket=self.bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
        )

        s3deploy.BucketDeployment(
            self,
            "DeployConfig",
            sources=[s3deploy.Source.json_data("config.json", {"apiUrl": api_url})],
            destination_bucket=self.bucket,
            distribution=self.distribution,
            distribution_paths=["/config.json"],
        )

        CfnOutput(
            scope,
            "SiteUrl",
            value=f"https://{self.distribution.distribution_domain_name}",
        )
        CfnOutput(scope, "SiteBucketName", value=self.bucket.bucket_name)
        CfnOutput(scope, "DistributionId", value=self.distribution.distribution_id)
