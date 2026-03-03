#!/usr/bin/env python3
"""CDK app entry point for the Stocks Serverless Pipeline."""

import aws_cdk as cdk

from stacks.pipeline_stack import PipelineStack

app = cdk.App()

PipelineStack(
    app,
    "StocksPipelineStack",
    env=cdk.Environment(region="us-east-1"),
)

app.synth()
