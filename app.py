#!/usr/bin/env python3
import aws_cdk as cdk

from infra.smstack import StateMachineStack
from infra.dbstack import DatabaseStack


app = cdk.App()
db_stack = DatabaseStack(app, "DatabaseStack")
sm_stack = StateMachineStack(
    app, 
    "StateMachineStack", 
    vpc=db_stack.vpc, 
    lambda_sg=db_stack.lambda_sg, 
    lambda_role=db_stack.lambda_role,
    lambda_layer=db_stack.lambda_layer,
    db_host=db_stack.db_host, 
    db_user=db_stack.db_user, 
    db_port=db_stack.db_port,
    db_name=db_stack.db_name,
    secret=db_stack.secret,
)

app.synth()
