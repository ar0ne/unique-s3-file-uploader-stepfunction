#!/usr/bin/env python3
import aws_cdk as cdk

from infra.stepstack import StepMachineStack
from infra.dbstack import DatabaseStack


app = cdk.App()
db_stack = DatabaseStack(app, "DatabaseStack")
sm_stack = StepMachineStack(
    app, 
    "StepMachineStack", 
    vpc=db_stack.vpc, 
    lambda_sg=db_stack.lambda_sg, 
    lambda_layer=db_stack.lambda_layer,
    db_host=db_stack.db_host, 
    db_user=db_stack.db_user, 
    db_port=db_stack.db_port,
    db_name=db_stack.db_name,
    db_password=db_stack.db_password,
)

app.synth()
