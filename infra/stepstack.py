import os
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_s3,
    aws_events,
    aws_iam as iam,
    aws_events_targets,
    RemovalPolicy,
)
from constructs import Construct


dirname = os.path.dirname(__file__)


class StepMachineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # TODO: it's temporary bucket, but we need to determine 'user_id' and 'folder'.
        s3_bucket = aws_s3.Bucket(
            self,
            "s3bucket",
            event_bridge_enabled=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # general warehouse for files
        gallery_s3_bucket = aws_s3.Bucket(
            self, "gallerybucket", removal_policy=RemovalPolicy.DESTROY
        )

        read_from_user_s3_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject"],
            resources=[s3_bucket.bucket_arn + "/*"],
        )
        list_user_s3_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:ListBucket"],
            resources=[s3_bucket.bucket_arn]
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
            "gethashfunction",
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
            environment={"TABLE_NAME": "Records"},  # TODO
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

        unique_file = sfn.Condition.boolean_equals("$.exists", False)
        record_exists_choice_statement = sfn.Choice(self, "Unique file?")
        record_exists_choice_statement.when(
            unique_file,
            copy_file.next(delete_file),
        ).otherwise(sfn.Pass(self, "Pass If File Already Exists").next(delete_file))

        state_machine = sfn.StateMachine(
            self,
            "UniqueFileStateMachine",
            definition=file_uploaded.next(create_new_record).next(
                record_exists_choice_statement
            ),
        )

        event_rule = aws_events.Rule(
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
