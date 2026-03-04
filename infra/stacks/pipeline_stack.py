from aws_cdk import Stack
from constructs import Construct

from .constructs.api import Api
from .constructs.database import Database
from .constructs.frontend import Frontend
from .constructs.ingestion import Ingestion


class PipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        db = Database(self, "Database")
        Ingestion(self, "Ingestion", table=db.table)
        api = Api(self, "Api", table=db.table)
        Frontend(self, "Frontend", api_url=api.api_url)
