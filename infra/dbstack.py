import os
import json
from aws_cdk import (
    CustomResource,
    Duration,
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_iam as iam,
    aws_secretsmanager as sm,
    aws_lambda as lambda_,
    custom_resources as cr,
)
from constructs import Construct


DB_PORT = 3306
DB_USER = "dbadmin"
DB_NAME = "myapp"


dirname = os.path.dirname(__file__)

class DatabaseStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(
            self, "VPC", ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"), max_azs=2
        )

        rds_secret = sm.Secret(
            self,
            "RDS-Secret",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"username": DB_USER}),
                    generate_string_key="password",
                    password_length=16,
                    exclude_punctuation=True
                )
        )

        db_sg = ec2.SecurityGroup(
            self,
            "RDS-SG",
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name="RDS SecurityGroup",
        )
        # access from proxy to DB cluster
        db_sg.add_ingress_rule(db_sg, ec2.Port.tcp(DB_PORT))

        db_cluster = rds.DatabaseCluster(
            self,
            "DatabaseCluster",
            vpc=vpc,
            engine=rds.DatabaseClusterEngine.aurora_mysql(
                version=rds.AuroraMysqlEngineVersion.VER_3_07_0
            ),
            credentials=rds.Credentials.from_secret(rds_secret),
            default_database_name="myapp",
            readers=[
                # rds.ClusterInstance.provisioned("reader1", promotion_tier=1),
                rds.ClusterInstance.serverless_v2("reader2"),
            ],
            writer=rds.ClusterInstance.provisioned("writer",
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.R6G, ec2.InstanceSize.LARGE)
            ),
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[db_sg],
        )

        proxy_role = iam.Role(
            self, "ProxyRole", assumed_by=iam.ServicePrincipal("rds.amazonaws.com")
        )

        proxy = rds.DatabaseProxy(
            self,
            "RDS-Proxy",
            proxy_target=rds.ProxyTarget.from_cluster(db_cluster),
            secrets=[rds_secret],
            vpc=vpc,
            role=proxy_role,
            security_groups=[db_sg],
            iam_auth=False,
            require_tls=False,
        )

        lambda_sg = ec2.SecurityGroup(
            self, "LambdaSG", vpc=vpc, allow_all_outbound=True
        )

        # access from lambda to RDS Proxy
        db_sg.add_ingress_rule(lambda_sg, ec2.Port.tcp(DB_PORT))

        lambda_role = iam.Role(
            self, "LambdaRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["rds-db:connect"],
                resources=[
                    f"arn:aws:rds-db:{self.region}:{self.account}:dbuser:*/{DB_USER}"
                ],
            )
        )

        db_init_function = lambda_.Function(
            self,
            "DB Init",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="init_db_handler.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(dirname, "../lambda")),
            timeout=Duration.seconds(30),
            environment={
                "DB_HOST": proxy.endpoint,
                "DB_USER": DB_USER,
                "DB_NAME": DB_NAME,
                "DB_PORT": str(DB_PORT),
                "DB_PASSWORD": rds_secret.secret_value_from_json("password").unsafe_unwrap()  # TODO: call SM in lambda instead
            },
            vpc=vpc,
            role=lambda_role,
            security_groups=[lambda_sg],
            memory_size=128,
        )

        provider = cr.Provider(self, "DBInitProvider", on_event_handler=db_init_function)

        resource = CustomResource(self, "DBInitCustomResource", service_token=provider.service_token, resource_type="Custom::InitDBProvider", properties={
            "sql_script": "" # TODO: should I hardcode path to file or provide/read in stack definition
        })
        resource.node.add_dependency(proxy)

        self.db_host = proxy.endpoint
        self.db_user = DB_USER
        self.db_port = str(DB_PORT)
        self.db_password = rds_secret.secret_value_from_json("password").unsafe_unwrap()  # TODO: call SM in lambda instead
        self.db_name = DB_NAME
        self.lambda_sg = lambda_sg
        self.vpc = vpc
