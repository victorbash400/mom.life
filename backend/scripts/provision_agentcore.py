"""Provision or update the mom.life AgentCore runtime with scoped AWS resources."""
from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import secrets
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError


PROJECT = Path(__file__).resolve().parents[2]
ARCHIVE = PROJECT / ".build" / "agentcore" / "mom-life-agentcore.zip"
STATE = PROJECT / ".build" / "cloud.json"
NAME = "mom-life"


def tags(name: str) -> list[dict[str, str]]:
    return [{"Key": "Name", "Value": name}, {"Key": "Project", "Value": NAME}]


def load_environment() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PROJECT / "backend" / ".env").read_text().splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if key.startswith("MOM_LIFE_") and key not in {"MOM_LIFE_AWS_PROFILE", "MOM_LIFE_AGENTCORE_RUNTIME_ARN"}:
            values[key] = value
    if not values.get("MOM_LIFE_DATABASE_URL"):
        raise RuntimeError("backend/.env must contain MOM_LIFE_DATABASE_URL.")
    connection_key = PROJECT / "backend" / "data" / "connection.key"
    if connection_key.is_file():
        values.setdefault("MOM_LIFE_CONNECTION_KEY", connection_key.read_text().strip())
    database = urlsplit(values["MOM_LIFE_DATABASE_URL"])
    query = dict(parse_qsl(database.query))
    if query.get("sslmode") in {"verify-ca", "verify-full"} and "sslrootcert" not in query:
        query["sslrootcert"] = "aws-rds-global-bundle.pem"
        values["MOM_LIFE_DATABASE_URL"] = urlunsplit((database.scheme, database.netloc, database.path, urlencode(query), database.fragment))
    return values


def ensure_bucket(s3, account_id: str, region: str) -> str:
    name = f"mom-life-agentcore-{account_id}-{region}"
    try:
        s3.head_bucket(Bucket=name)
    except ClientError as error:
        if error.response.get("ResponseMetadata", {}).get("HTTPStatusCode") not in {403, 404}:
            raise
        request = {"Bucket": name}
        if region != "us-east-1":
            request["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**request)
        s3.put_public_access_block(
            Bucket=name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        s3.put_bucket_encryption(
            Bucket=name,
            ServerSideEncryptionConfiguration={"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]},
        )
    return name


def ensure_secret(client, environment: dict[str, str]) -> str:
    name = "mom-life/runtime-config"
    try:
        current = client.describe_secret(SecretId=name)
        previous = json.loads(client.get_secret_value(SecretId=name)["SecretString"])
        environment.setdefault("MOM_LIFE_CONNECTION_KEY", previous.get("MOM_LIFE_CONNECTION_KEY", ""))
        if not environment["MOM_LIFE_CONNECTION_KEY"]:
            environment["MOM_LIFE_CONNECTION_KEY"] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        payload = json.dumps(environment)
        client.put_secret_value(SecretId=name, SecretString=payload)
        return current["ARN"]
    except client.exceptions.ResourceNotFoundException:
        environment["MOM_LIFE_CONNECTION_KEY"] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        payload = json.dumps(environment)
        return client.create_secret(Name=name, Description="mom.life runtime configuration", SecretString=payload, Tags=tags(name))["ARN"]


def ensure_memory(client) -> tuple[str, str]:
    response = client.list_memories(maxResults=100)
    memory = None
    for summary in response.get("memories", []):
        details = client.get_memory(memoryId=summary["id"]).get("memory", {})
        if details.get("name") == "momLifeMemory":
            memory = details
            break
    if not memory:
        memory = client.create_memory(name="momLifeMemory", description="mom.life Strands chat history", eventExpiryDuration=90)["memory"]
    return str(memory["id"]), str(memory["arn"])


def ensure_role(iam, account_id: str, region: str, bucket: str, secret_arn: str, memory_arn: str, environment: dict[str, str]) -> str:
    name = "mom-life-agentcore-runtime"
    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": account_id},
                "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/*"},
            },
        }],
    }
    try:
        role = iam.get_role(RoleName=name)["Role"]
        iam.update_assume_role_policy(RoleName=name, PolicyDocument=json.dumps(trust))
    except iam.exceptions.NoSuchEntityException:
        role = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Description="Runs mom.life Strands agents in AgentCore")["Role"]
    statements = [
        {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": f"arn:aws:s3:::{bucket}/*"},
        {"Effect": "Allow", "Action": ["secretsmanager:GetSecretValue"], "Resource": secret_arn},
        {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:DescribeLogStreams", "logs:PutLogEvents"], "Resource": f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"},
        {"Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"], "Resource": ["arn:aws:bedrock:*::foundation-model/*", f"arn:aws:bedrock:{region}:{account_id}:*"]},
        {"Effect": "Allow", "Action": ["bedrock-agentcore:CreateEvent", "bedrock-agentcore:GetEvent", "bedrock-agentcore:DeleteEvent", "bedrock-agentcore:ListEvents", "bedrock-agentcore:RetrieveMemoryRecords"], "Resource": memory_arn},
        {"Effect": "Allow", "Action": ["bedrock-agentcore:StartBrowserSession", "bedrock-agentcore:StopBrowserSession", "bedrock-agentcore:GetBrowserSession", "bedrock-agentcore:InvokeBrowser", "bedrock-agentcore:UpdateBrowserStream"], "Resource": f"arn:aws:bedrock-agentcore:{region}:{account_id}:browser/*"},
    ]
    schedule_group = environment.get("MOM_LIFE_AUTOMATION_SCHEDULE_GROUP", "mom-life")
    statements.append({"Effect": "Allow", "Action": ["scheduler:CreateSchedule", "scheduler:UpdateSchedule", "scheduler:GetSchedule", "scheduler:DeleteSchedule"], "Resource": f"arn:aws:scheduler:{region}:{account_id}:schedule/{schedule_group}/*"})
    automation_role = environment.get("MOM_LIFE_AUTOMATION_ROLE_ARN")
    if automation_role:
        statements.append({"Effect": "Allow", "Action": "iam:PassRole", "Resource": automation_role, "Condition": {"StringEquals": {"iam:PassedToService": "scheduler.amazonaws.com"}}})
    iam.put_role_policy(RoleName=name, PolicyName="mom-life-agentcore-runtime", PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}))
    return role["Arn"]


def ensure_network(ec2, rds) -> tuple[list[str], str, str]:
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        raise RuntimeError("The account has no default VPC.")
    vpc = vpcs[0]
    vpc_id = vpc["VpcId"]
    existing = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
    public = [item for item in existing if item.get("MapPublicIpOnLaunch")]
    if not public:
        raise RuntimeError("The default VPC has no public subnet for the NAT gateway.")
    azs = sorted({item["AvailabilityZone"] for item in existing})
    private = [item for item in existing if any(tag.get("Key") == "Project" and tag.get("Value") == NAME for tag in item.get("Tags", []))]
    used = [ipaddress.ip_network(item["CidrBlock"]) for item in existing]
    candidates = [net for net in ipaddress.ip_network(vpc["CidrBlock"]).subnets(new_prefix=24) if not any(net.overlaps(item) for item in used)]
    while len(private) < 2:
        if not candidates or len(azs) < 2:
            raise RuntimeError("Two free private subnet ranges and availability zones are required.")
        index = len(private)
        subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock=str(candidates.pop()), AvailabilityZone=azs[index], TagSpecifications=[{"ResourceType": "subnet", "Tags": tags(f"mom-life-agentcore-private-{index + 1}")}])["Subnet"]
        private.append(subnet)
    allocations = ec2.describe_addresses(Filters=[{"Name": "tag:Project", "Values": [NAME]}]).get("Addresses", [])
    if allocations:
        allocation_id = allocations[0]["AllocationId"]
    else:
        allocation_id = ec2.allocate_address(Domain="vpc", TagSpecifications=[{"ResourceType": "elastic-ip", "Tags": tags("mom-life-agentcore-nat")}])["AllocationId"]
    gateways = ec2.describe_nat_gateways(Filter=[{"Name": "tag:Project", "Values": [NAME]}, {"Name": "state", "Values": ["pending", "available"]}]).get("NatGateways", [])
    if gateways:
        gateway = gateways[0]
    else:
        gateway = ec2.create_nat_gateway(SubnetId=public[0]["SubnetId"], AllocationId=allocation_id, TagSpecifications=[{"ResourceType": "natgateway", "Tags": tags("mom-life-agentcore-nat")}])["NatGateway"]
    if gateway["State"] != "available":
        raise RuntimeError(f"NAT gateway {gateway['NatGatewayId']} is {gateway['State']}; run this command again after AWS marks it available.")
    route_tables = ec2.describe_route_tables(Filters=[{"Name": "tag:Name", "Values": ["mom-life-agentcore-private"]}])["RouteTables"]
    route_table = route_tables[0] if route_tables else ec2.create_route_table(VpcId=vpc_id, TagSpecifications=[{"ResourceType": "route-table", "Tags": tags("mom-life-agentcore-private")}])["RouteTable"]
    routes = route_table.get("Routes", [])
    if not any(route.get("DestinationCidrBlock") == "0.0.0.0/0" for route in routes):
        ec2.create_route(RouteTableId=route_table["RouteTableId"], DestinationCidrBlock="0.0.0.0/0", NatGatewayId=gateway["NatGatewayId"])
    associations = {item.get("SubnetId") for item in route_table.get("Associations", [])}
    for subnet in private[:2]:
        if subnet["SubnetId"] not in associations:
            ec2.associate_route_table(RouteTableId=route_table["RouteTableId"], SubnetId=subnet["SubnetId"])
    groups = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": ["mom-life-agentcore"]}, {"Name": "vpc-id", "Values": [vpc_id]}])["SecurityGroups"]
    group_id = groups[0]["GroupId"] if groups else ec2.create_security_group(GroupName="mom-life-agentcore", Description="mom.life AgentCore runtime", VpcId=vpc_id, TagSpecifications=[{"ResourceType": "security-group", "Tags": tags("mom-life-agentcore")}])["GroupId"]
    database = rds.describe_db_instances(DBInstanceIdentifier="mom-life")["DBInstances"][0]
    db_group = database["VpcSecurityGroups"][0]["VpcSecurityGroupId"]
    try:
        ec2.authorize_security_group_ingress(GroupId=db_group, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432, "UserIdGroupPairs": [{"GroupId": group_id, "Description": "mom.life AgentCore"}]}])
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "InvalidPermission.Duplicate":
            raise
    return [item["SubnetId"] for item in private[:2]], group_id, gateway["NatGatewayId"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="operator-provisioning")
    args = parser.parse_args()
    region = "us-east-1"
    session = boto3.Session(profile_name=args.profile, region_name=region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    environment = load_environment()
    bucket = ensure_bucket(session.client("s3"), account_id, region)
    secret_arn = ensure_secret(session.client("secretsmanager"), environment)
    memory_id, memory_arn = ensure_memory(session.client("bedrock-agentcore-control"))
    role_arn = ensure_role(session.client("iam"), account_id, region, bucket, secret_arn, memory_arn, environment)
    subnets, security_group, nat_gateway = ensure_network(session.client("ec2"), session.client("rds"))
    if not ARCHIVE.is_file():
        raise RuntimeError("Run backend/scripts/package_agentcore.py first.")
    key = "runtime/mom-life-agentcore.zip"
    session.client("s3").upload_file(str(ARCHIVE), bucket, key, ExtraArgs={"ExpectedBucketOwner": account_id})
    control = session.client("bedrock-agentcore-control")
    existing = next((item for item in control.list_agent_runtimes(maxResults=100).get("agentRuntimes", []) if item.get("agentRuntimeName") == "momLifeRuntime"), None)
    artifact = {"codeConfiguration": {"code": {"s3": {"bucket": bucket, "prefix": key}}, "runtime": "PYTHON_3_14", "entryPoint": ["agentcore_main.py"]}}
    network = {"networkMode": "VPC", "networkModeConfig": {"subnets": subnets, "securityGroups": [security_group]}}
    runtime_environment = {"MOM_LIFE_CONFIG_SECRET_ARN": secret_arn, "MOM_LIFE_AGENTCORE_MEMORY_ID": memory_id, "MOM_LIFE_STRANDS_REGION": region}
    if existing:
        response = control.update_agent_runtime(agentRuntimeId=existing["agentRuntimeId"], agentRuntimeArtifact=artifact, roleArn=role_arn, networkConfiguration=network, environmentVariables=runtime_environment)
    else:
        response = control.create_agent_runtime(agentRuntimeName="momLifeRuntime", description="mom.life Strands agents", agentRuntimeArtifact=artifact, roleArn=role_arn, networkConfiguration=network, environmentVariables=runtime_environment, lifecycleConfiguration={"idleRuntimeSessionTimeout": 300, "maxLifetime": 28800}, clientToken=str(uuid4()), tags={"Project": NAME})
    state = {"region": region, "artifact_bucket": bucket, "config_secret_arn": secret_arn, "memory_id": memory_id, "memory_arn": memory_arn, "runtime_id": response.get("agentRuntimeId") or existing.get("agentRuntimeId"), "runtime_arn": response.get("agentRuntimeArn") or existing.get("agentRuntimeArn"), "runtime_status": response.get("status"), "runtime_role_arn": role_arn, "private_subnets": subnets, "runtime_security_group": security_group, "nat_gateway": nat_gateway}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({key: state[key] for key in ("memory_id", "runtime_id", "runtime_arn", "runtime_status", "nat_gateway")}, indent=2))


if __name__ == "__main__":
    main()
