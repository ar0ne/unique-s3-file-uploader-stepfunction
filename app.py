#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.stepstack import StepMachineStack
from infra.dbstack import DatabaseStack


app = cdk.App()
StepMachineStack(app, "StepMachineStack")
DatabaseStack(app, "DatabaseStack")

app.synth()
