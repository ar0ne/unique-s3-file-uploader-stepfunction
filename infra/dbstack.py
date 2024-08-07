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
    CfnParameter,
)
from constructs import Construct


LAYER_ARN = "arn:aws:lambda:{region}:{account}:layer:pymysql-layer"


dirname = os.path.dirname(__file__)


class DatabaseStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        port = CfnParameter(
            self, "DB_PORT", description="Database Port", default=3306, type="Number"
        )
        user = CfnParameter(
            self,
            "DB_USER",
            description="Database User",
            default="dbadmin",
            type="String",
        )
        dbname = CfnParameter(
            self,
            "DB_NAME",
            description="Name of Database",
            default="myapp",
            type="String",
        )

        vpc = ec2.Vpc(
            self, "VPC", ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"), max_azs=2
        )

        rds_secret = sm.Secret(
            self,
            "RDS Secret",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"username": user.value_as_string}),
                generate_string_key="password",
                password_length=16,
                exclude_punctuation=True,
            ),
        )

        db_sg = ec2.SecurityGroup(
            self,
            "RDS SG",
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name="RDS SecurityGroup",
        )
        # access from proxy to DB cluster
        db_sg.add_ingress_rule(db_sg, ec2.Port.tcp(port.value_as_number))

        db_cluster = rds.DatabaseCluster(
            self,
            "DatabaseCluster",
            vpc=vpc,
            engine=rds.DatabaseClusterEngine.aurora_mysql(
                version=rds.AuroraMysqlEngineVersion.VER_3_07_0
            ),
            credentials=rds.Credentials.from_secret(rds_secret),
            default_database_name=dbname.value_as_string,
            readers=[
                # rds.ClusterInstance.provisioned("reader1", promotion_tier=1),
                rds.ClusterInstance.serverless_v2("reader2"),
            ],
            writer=rds.ClusterInstance.provisioned(
                "writer",
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.R6G, ec2.InstanceSize.LARGE
                ),
            ),
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[db_sg],
        )

        proxy_role = iam.Role(
            self, "Proxy Role", assumed_by=iam.ServicePrincipal("rds.amazonaws.com")
        )

        proxy = rds.DatabaseProxy(
            self,
            "RDS Proxy",
            proxy_target=rds.ProxyTarget.from_cluster(db_cluster),
            secrets=[rds_secret],
            vpc=vpc,
            role=proxy_role,
            security_groups=[db_sg],
            iam_auth=False,
            require_tls=False,
        )

        lambda_sg = ec2.SecurityGroup(
            self, "Lambda SG", vpc=vpc, allow_all_outbound=True
        )

        # access from lambda to RDS Proxy
        db_sg.add_ingress_rule(lambda_sg, ec2.Port.tcp(port.value_as_number))

        lambda_role = iam.Role(
            self, "Lambda Role", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
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
                    f"arn:aws:rds-db:{self.region}:{self.account}:dbuser:*/{user.value_as_string}"
                ],
            )
        )

        pymysql_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "PyMySQL Layer",
            LAYER_ARN.format(region=self.region, account=self.account),
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
                "DB_USER": user.value_as_string,
                "DB_NAME": dbname.value_as_string,
                "DB_PORT": port.value_as_string,
                "DB_PASSWORD": rds_secret.secret_value_from_json(
                    "password"
                ).unsafe_unwrap(),  # TODO: call SM in lambda instead
            },
            vpc=vpc,
            role=lambda_role,
            security_groups=[lambda_sg],
            memory_size=128,
            layers=[pymysql_layer],
        )

        provider = cr.Provider(
            self, "DBInit Provider", on_event_handler=db_init_function
        )

        resource = CustomResource(
            self,
            "DBInit CustomResource",
            service_token=provider.service_token,
            resource_type="Custom::InitDBProvider",
        )
        resource.node.add_dependency(proxy)

        self.db_user = user.value_as_string
        self.db_port = port.value_as_string
        self.db_host = proxy.endpoint
        self.db_name = dbname.value_as_string
        self.db_password = rds_secret.secret_value_from_json("password").unsafe_unwrap()
        self.lambda_sg = lambda_sg
        self.vpc = vpc
        self.lambda_layer = pymysql_layer
