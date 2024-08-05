import aws_cdk as core
import aws_cdk.assertions as assertions

from unique_s3_file_step_function.unique_s3_file_step_function_stack import UniqueS3FileStepFunctionStack

# example tests. To run these tests, uncomment this file along with the example
# resource in unique_s3_file_step_function/unique_s3_file_step_function_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = UniqueS3FileStepFunctionStack(app, "unique-s3-file-step-function")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
