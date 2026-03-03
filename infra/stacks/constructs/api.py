"""API construct: Lambda + API Gateway REST API with CORS."""

import os

import aws_cdk as cdk
import aws_cdk.aws_apigateway as apigw
import aws_cdk.aws_lambda as lambda_
from constructs import Construct
from aws_cdk.aws_dynamodb import ITable

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")


class Api(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        table: ITable,
    ) -> None:
        super().__init__(scope, id)

        self.function = lambda_.Function(
            self,
            "Handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                os.path.join(BACKEND_DIR, "lambdas", "api")
            ),
            timeout=cdk.Duration.seconds(10),
            memory_size=256,
            environment={
                "TABLE_NAME": table.table_name,
            },
        )

        table.grant_read_data(self.function)

        rest_api = apigw.RestApi(
            self,
            "MoversApi",
            rest_api_name="StocksMoversApi",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
            ),
        )

        movers_resource = rest_api.root.add_resource("movers")
        movers_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.function),
        )

        self.api_url = rest_api.url.rstrip("/")
