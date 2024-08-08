import os
from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_s3,
    aws_ec2 as ec2,
    aws_events,
    aws_iam as iam,
    aws_events_targets,
    RemovalPolicy,
)
from constructs import Construct


dirname = os.path.dirname(__file__)


class StateMachineStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        db_host: str,
        db_user: str,
        db_name: str,
        db_port: int,
        lambda_sg: ec2.SecurityGroup,
        lambda_role: iam.Role,
        lambda_layer: lambda_.LayerVersion,
        secret: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        s3_bucket = aws_s3.Bucket(
            self,
            "s3bucket",
            event_bridge_enabled=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # general warehouse for files
        gallery_s3_bucket = aws_s3.Bucket(
            self,
            "gallerybucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        read_from_user_s3_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject"],
            resources=[s3_bucket.bucket_arn + "/*"],
        )
        list_user_s3_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:ListBucket"],
            resources=[s3_bucket.bucket_arn],
        )
        write_to_gallery_s3_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject"],
            resources=[gallery_s3_bucket.bucket_arn + "/*"],
        )
        delete_from_s3_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:DeleteObject"],
            resources=[s3_bucket.bucket_arn + "/*"],
        )

        get_hash_function = lambda_.Function(
            self,
            "GetHashFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="hash_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "../lambda")),
        )
        create_new_db_record_function = lambda_.Function(
            self,
            "NewRecordFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="record_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "../lambda")),
            environment={
                "TABLE_NAME": "records",
                "DB_USER": db_user,
                "DB_PORT": str(db_port),
                "DB_NAME": db_name,
                "DB_HOST": db_host,
                "SECRET": secret,
            },
            role=lambda_role,
            vpc=vpc,
            security_groups=[lambda_sg],
            timeout=Duration.seconds(30),
            layers=[lambda_layer],
        )
        delete_object_from_s3_function = lambda_.Function(
            self,
            "DeleteFileFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="delete_file_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "../lambda")),
        )
        copy_file_to_s3_gallery_function = lambda_.Function(
            self,
            "CopyFileFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="copy_file_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "../lambda")),
            environment={
                "COPY_TO_BUCKET": gallery_s3_bucket.bucket_name,
            },
        )

        get_hash_function.add_to_role_policy(read_from_user_s3_bucket_policy)
        get_hash_function.add_to_role_policy(list_user_s3_bucket_policy)
        delete_object_from_s3_function.add_to_role_policy(delete_from_s3_bucket_policy)
        copy_file_to_s3_gallery_function.add_to_role_policy(
            read_from_user_s3_bucket_policy
        )
        copy_file_to_s3_gallery_function.add_to_role_policy(
            write_to_gallery_s3_bucket_policy
        )

        file_uploaded = tasks.LambdaInvoke(
            self,
            "New File Uploaded",
            lambda_function=get_hash_function,
            payload_response_only=True,
        )
        create_new_record = tasks.LambdaInvoke(
            self,
            "Create New Record",
            lambda_function=create_new_db_record_function,
            payload_response_only=True,
        )

        delete_file = tasks.LambdaInvoke(
            self,
            "Delete File",
            lambda_function=delete_object_from_s3_function,
            payload_response_only=True,
        )
        copy_file = tasks.LambdaInvoke(
            self,
            "Copy File To Gallery",
            lambda_function=copy_file_to_s3_gallery_function,
            payload_response_only=True,
        )

        is_unique_file = sfn.Condition.boolean_equals("$.exists", False)
        record_exists_choice = sfn.Choice(self, "Unique file?")
        record_exists_choice.when(
            is_unique_file,
            copy_file.next(delete_file),
        ).otherwise(sfn.Pass(self, "Pass If File Already Exists").next(delete_file))

        chain = file_uploaded.next(create_new_record).next(record_exists_choice)

        state_machine = sfn.StateMachine(
            self,
            "UniqueFileStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.minutes(1),
        )

        aws_events.Rule(
            self,
            "NewFileEventConsumer",
            description="New file uploaded event",
            event_pattern=aws_events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={"bucket": {"name": [s3_bucket.bucket_name]}},
            ),
            targets=[aws_events_targets.SfnStateMachine(state_machine)],
        )

        CfnOutput(self, "Upload bucket", value=s3_bucket.bucket_name)
        CfnOutput(self, "File catalog s3 bucket", value=gallery_s3_bucket.bucket_name)
