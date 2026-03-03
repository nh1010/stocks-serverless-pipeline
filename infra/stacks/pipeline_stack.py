"""Main CDK stack composing all constructs for the Stocks Pipeline."""

import aws_cdk as cdk
from constructs import Construct

from stacks.constructs.database import Database
from stacks.constructs.ingestion import Ingestion
from stacks.constructs.api import Api
from stacks.constructs.frontend import Frontend


class PipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        massive_api_key = self.node.try_get_context("massive_api_key") or ""

        database = Database(self, "Database")

        ingestion = Ingestion(
            self,
            "Ingestion",
            table=database.table,
            massive_api_key=massive_api_key,
        )

        api = Api(self, "Api", table=database.table)

        frontend = Frontend(self, "Frontend", api_url=api.api_url)

        cdk.CfnOutput(self, "ApiUrl", value=api.api_url)
        cdk.CfnOutput(self, "FrontendUrl", value=frontend.distribution_url)
