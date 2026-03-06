from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_ssm as ssm,
)
from constructs import Construct

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SSM_PARAM_NAME = "/stocks-pipeline/massive-api-key"


class Ingestion(Construct):
    def __init__(self, scope: Construct, id: str, *, table, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        api_key_param = ssm.StringParameter.from_secure_string_parameter_attributes(
            self, "MassiveApiKey", parameter_name=SSM_PARAM_NAME
        )

        # Role used by EventBridge Scheduler to invoke the Lambda on retries
        scheduler_role = iam.Role(
            self,
            "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )

        self.handler = _lambda.Function(
            self,
            "Handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(
                str(PROJECT_ROOT / "backend" / "lambdas" / "ingestion")
            ),
            environment={
                "TABLE_NAME": table.table_name,
                "SSM_API_KEY_NAME": SSM_PARAM_NAME,
                "SCHEDULER_ROLE_ARN": scheduler_role.role_arn,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        table.grant_write_data(self.handler)
        api_key_param.grant_read(self.handler)

        # Let the scheduler role invoke the Lambda
        self.handler.grant_invoke(scheduler_role)

        # Let the Lambda create/delete one-time retry schedules
        self.handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["scheduler:CreateSchedule", "scheduler:DeleteSchedule"],
                resources=["arn:aws:scheduler:*:*:schedule/default/ingestion-retry-*"],
            )
        )
        self.handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[scheduler_role.role_arn],
            )
        )

        rule = events.Rule(
            self,
            "DailyTrigger",
            schedule=events.Schedule.cron(
                minute="0", hour="11", week_day="MON-FRI"
            ),
        )
        rule.add_target(targets.LambdaFunction(self.handler))

        CfnOutput(scope, "IngestionFunctionName", value=self.handler.function_name)
