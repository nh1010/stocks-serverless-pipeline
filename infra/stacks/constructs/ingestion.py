"""Ingestion construct: Lambda + EventBridge cron + SSM parameter."""

import os

import aws_cdk as cdk
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_ssm as ssm
from constructs import Construct
from aws_cdk.aws_dynamodb import ITable

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")


class Ingestion(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        table: ITable,
        massive_api_key: str,
    ) -> None:
        super().__init__(scope, id)

        param = ssm.StringParameter(
            self,
            "MassiveApiKey",
            parameter_name="/stocks-pipeline/massive-api-key",
            string_value=massive_api_key or "PLACEHOLDER",
            tier=ssm.ParameterTier.STANDARD,
        )

        layer = lambda_.LayerVersion(
            self,
            "DepsLayer",
            code=lambda_.Code.from_asset(
                os.path.join(BACKEND_DIR, "layer"),
                bundling=cdk.BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output/python",
                    ],
                ),
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Shared Python dependencies (requests)",
        )

        self.function = lambda_.Function(
            self,
            "Handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                os.path.join(BACKEND_DIR, "lambdas", "ingestion")
            ),
            layers=[layer],
            timeout=cdk.Duration.seconds(30),
            memory_size=256,
            environment={
                "TABLE_NAME": table.table_name,
                "SSM_PARAM_NAME": param.parameter_name,
            },
        )

        table.grant_write_data(self.function)
        param.grant_read(self.function)

        self.layer = layer

        rule = events.Rule(
            self,
            "DailyCron",
            schedule=events.Schedule.cron(
                minute="30", hour="21", week_day="MON-FRI"
            ),
        )
        rule.add_target(targets.LambdaFunction(self.function))
