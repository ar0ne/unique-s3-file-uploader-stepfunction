import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    # Create a Secrets Manager client
    client = boto3.client('secretsmanager')

    try:
        # Attempt to retrieve the secret value
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # Handle the exception if the secret can't be retrieved
        raise e

    # If there's no exception, process the retrieved secret
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
    else:
        # For binary secrets, decode them before using
        secret = get_secret_value_response['SecretBinary'].decode('utf-8')
    return secret

