#!/usr/bin/env python3
import os

import aws_cdk as cdk

from step.stepstack import UniqueS3FileStepFunctionStack


app = cdk.App()
UniqueS3FileStepFunctionStack(app, "UniqueS3FileStepFunctionStack",
)

app.synth()
