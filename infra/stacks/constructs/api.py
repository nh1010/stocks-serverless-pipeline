from pathlib import Path

from aws_cdk import CfnOutput, Duration, aws_apigateway as apigw, aws_lambda as _lambda
from constructs import Construct

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Api(Construct):
    def __init__(self, scope: Construct, id: str, *, table, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.handler = _lambda.Function(
            self,
            "Handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(
                str(PROJECT_ROOT / "backend" / "lambdas" / "api")
            ),
            environment={
                "TABLE_NAME": table.table_name,
            },
            timeout=Duration.seconds(10),
            memory_size=128,
        )

        table.grant_read_data(self.handler)

        self.rest_api = apigw.RestApi(
            self,
            "RestApi",
            rest_api_name="StocksMoversApi",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
            ),
        )

        movers = self.rest_api.root.add_resource("movers")
        movers.add_method("GET", apigw.LambdaIntegration(self.handler))

        self.api_url = self.rest_api.url

        CfnOutput(scope, "ApiUrl", value=self.api_url)
