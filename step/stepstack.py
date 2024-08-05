import os
from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


dirname = os.path.dirname(__file__)


class UniqueS3FileStepFunctionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        get_hash_function = lambda_.Function(
            self,
            "GetHashFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="hash_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "handlers")),
        )
        create_new_db_record_function = lambda_.Function(
            self,
            "NewRecordFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="record_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "handlers")),
        )
        delete_object_from_s3_function = lambda_.Function(
            self,
            "DeleteFileFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="delete_file_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "handlers")),
        )
        copy_file_to_s3_gallery_function = lambda_.Function(
            self,
            "CopyFileFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="copy_file_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "handlers")),
        )

        file_uploaded = tasks.LambdaInvoke(
            self, "NewFileUploaded", lambda_function=get_hash_function
        )
        create_new_record = tasks.LambdaInvoke(
            self, "CreateNewRecord", lambda_function=create_new_db_record_function
        )

        delete_file = tasks.LambdaInvoke(
            self, "DeleteFile", lambda_function=delete_object_from_s3_function
        )
        copy_file = tasks.LambdaInvoke(
            self, "CopyFileToGallery", lambda_function=copy_file_to_s3_gallery_function
        )

        unique_file = sfn.Condition.boolean_equals("$.exists", False)
        record_exists_choice_statement = sfn.Choice(self, "Record Already Exists?")
        record_exists_choice_statement.when(
            unique_file,
            copy_file.next(delete_file),
        ).otherwise(sfn.Pass(self, "PassIfFileAlreadyExists").next(delete_file))

        state_machine = sfn.StateMachine(
            self,
            "UniqueS3FileStateMachine",
            definition=file_uploaded.next(create_new_record).next(
                record_exists_choice_statement
            ),
        )
