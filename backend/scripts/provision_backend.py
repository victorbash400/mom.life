"""Provision the public FastAPI control plane on ECS Fargate and CloudFront."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


PROJECT = Path(__file__).resolve().parents[2]
STATE = PROJECT / ".build" / "cloud.json"
NAME = "mom-life"


def tag_spec(resource_type: str, name: str) -> list[dict]:
    return [{"ResourceType": resource_type, "Tags": [{"Key": "Name", "Value": name}, {"Key": "Project", "Value": NAME}]}]


def role(iam, name: str, service: str) -> dict:
    trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}]}
    try:
        result = iam.get_role(RoleName=name)["Role"]
        iam.update_assume_role_policy(RoleName=name, PolicyDocument=json.dumps(trust))
        return result
    except iam.exceptions.NoSuchEntityException:
        return iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Description=f"mom.life {name}")["Role"]


def ensure_repository(ecr, account_id: str, region: str) -> str:
    try:
        repository = ecr.describe_repositories(repositoryNames=["mom-life-backend"])["repositories"][0]
    except ecr.exceptions.RepositoryNotFoundException:
        repository = ecr.create_repository(repositoryName="mom-life-backend", imageScanningConfiguration={"scanOnPush": True}, encryptionConfiguration={"encryptionType": "AES256"}, tags=[{"Key": "Project", "Value": NAME}])["repository"]
    return repository["repositoryUri"]


def ensure_security_group(ec2, vpc_id: str, name: str, description: str) -> str:
    groups = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [name]}, {"Name": "vpc-id", "Values": [vpc_id]}])["SecurityGroups"]
    if groups:
        return groups[0]["GroupId"]
    return ec2.create_security_group(GroupName=name, Description=description, VpcId=vpc_id, TagSpecifications=tag_spec("security-group", name))["GroupId"]


def allow(ec2, group_id: str, permission: dict) -> None:
    try:
        ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=[permission])
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "InvalidPermission.Duplicate":
            raise


def ensure_load_balancer(session, vpc_id: str, public_subnets: list[str]) -> tuple[str, str, str]:
    ec2 = session.client("ec2")
    elb = session.client("elbv2")
    alb_group = ensure_security_group(ec2, vpc_id, "mom-life-alb", "CloudFront access to mom.life")
    prefix = ec2.describe_managed_prefix_lists(Filters=[{"Name": "prefix-list-name", "Values": ["com.amazonaws.global.cloudfront.origin-facing"]}])["PrefixLists"][0]["PrefixListId"]
    allow(ec2, alb_group, {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "PrefixListIds": [{"PrefixListId": prefix, "Description": "CloudFront origins"}]})
    task_group = ensure_security_group(ec2, vpc_id, "mom-life-backend", "mom.life FastAPI tasks")
    allow(ec2, task_group, {"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000, "UserIdGroupPairs": [{"GroupId": alb_group, "Description": "mom.life ALB"}]})
    balancers = elb.describe_load_balancers(Names=["mom-life-backend"])["LoadBalancers"] if _elb_exists(elb) else []
    if balancers:
        balancer = balancers[0]
    else:
        balancer = elb.create_load_balancer(Name="mom-life-backend", Subnets=public_subnets, SecurityGroups=[alb_group], Scheme="internet-facing", Type="application", IpAddressType="ipv4", Tags=[{"Key": "Project", "Value": NAME}])["LoadBalancers"][0]
    target_groups = elb.describe_target_groups(Names=["mom-life-backend"])["TargetGroups"] if _target_exists(elb) else []
    if target_groups:
        target_group = target_groups[0]
    else:
        target_group = elb.create_target_group(Name="mom-life-backend", Protocol="HTTP", Port=8000, VpcId=vpc_id, TargetType="ip", HealthCheckPath="/health", Matcher={"HttpCode": "200"}, Tags=[{"Key": "Project", "Value": NAME}])["TargetGroups"][0]
    listeners = elb.describe_listeners(LoadBalancerArn=balancer["LoadBalancerArn"])["Listeners"]
    if not listeners:
        elb.create_listener(LoadBalancerArn=balancer["LoadBalancerArn"], Protocol="HTTP", Port=80, DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group["TargetGroupArn"]}])
    elb.modify_load_balancer_attributes(LoadBalancerArn=balancer["LoadBalancerArn"], Attributes=[{"Key": "idle_timeout.timeout_seconds", "Value": "300"}])
    return balancer["DNSName"], target_group["TargetGroupArn"], task_group


def _elb_exists(elb) -> bool:
    try:
        elb.describe_load_balancers(Names=["mom-life-backend"])
        return True
    except elb.exceptions.LoadBalancerNotFoundException:
        return False


def _target_exists(elb) -> bool:
    try:
        elb.describe_target_groups(Names=["mom-life-backend"])
        return True
    except elb.exceptions.TargetGroupNotFoundException:
        return False


def ensure_distribution(cloudfront, alb_dns: str) -> tuple[str, str, str]:
    existing = next((item for item in cloudfront.list_distributions().get("DistributionList", {}).get("Items", []) if item.get("Comment") == "mom.life backend"), None)
    if existing:
        return existing["Id"], existing["DomainName"], existing["Status"]
    response = cloudfront.create_distribution(DistributionConfig={
        "CallerReference": "mom-life-backend-v1",
        "Comment": "mom.life backend",
        "Enabled": True,
        "HttpVersion": "http2and3",
        "Origins": {"Quantity": 1, "Items": [{"Id": "mom-life-alb", "DomainName": alb_dns, "CustomOriginConfig": {"HTTPPort": 80, "HTTPSPort": 443, "OriginProtocolPolicy": "http-only", "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]}, "OriginReadTimeout": 60, "OriginKeepaliveTimeout": 60}}]},
        "DefaultCacheBehavior": {
            "TargetOriginId": "mom-life-alb",
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {"Quantity": 7, "Items": ["GET", "HEAD", "OPTIONS", "PUT", "PATCH", "POST", "DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}},
            "Compress": True,
            "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
            "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
            "TrustedSigners": {"Enabled": False, "Quantity": 0},
            "TrustedKeyGroups": {"Enabled": False, "Quantity": 0},
        },
        "PriceClass": "PriceClass_100",
        "ViewerCertificate": {"CloudFrontDefaultCertificate": True, "MinimumProtocolVersion": "TLSv1.2_2021"},
        "Restrictions": {"GeoRestriction": {"RestrictionType": "none", "Quantity": 0}},
    })["Distribution"]
    return response["Id"], response["DomainName"], response["Status"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="operator-provisioning")
    parser.add_argument("--image-tag", default="latest")
    args = parser.parse_args()
    state = json.loads(STATE.read_text())
    environment = {
        line.split("=", 1)[0]: line.split("=", 1)[1].strip().strip('"').strip("'")
        for line in (PROJECT / "backend" / ".env").read_text().splitlines()
        if line.startswith("MOM_LIFE_") and "=" in line
    }
    region = state["region"]
    session = boto3.Session(profile_name=args.profile, region_name=region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    ecr = session.client("ecr")
    repository = ensure_repository(ecr, account_id, region)
    try:
        ecr.describe_images(repositoryName="mom-life-backend", imageIds=[{"imageTag": args.image_tag}])
    except ecr.exceptions.ImageNotFoundException:
        print(json.dumps({"repository": repository, "next": f"Push a linux/arm64 image tagged {args.image_tag}, then run this command again."}, indent=2))
        return
    iam = session.client("iam")
    execution = role(iam, "mom-life-ecs-execution", "ecs-tasks.amazonaws.com")
    iam.attach_role_policy(RoleName=execution["RoleName"], PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy")
    iam.put_role_policy(RoleName=execution["RoleName"], PolicyName="mom-life-secrets", PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": state["config_secret_arn"]}]}))
    task = role(iam, "mom-life-ecs-task", "ecs-tasks.amazonaws.com")
    task_statements = [
        {"Effect": "Allow", "Action": ["bedrock-agentcore:InvokeAgentRuntime", "bedrock-agentcore:StopRuntimeSession"], "Resource": [state["runtime_arn"], f"{state['runtime_arn']}/runtime-endpoint/*"]},
        {"Effect": "Allow", "Action": ["bedrock-agentcore:GetEvent", "bedrock-agentcore:ListEvents"], "Resource": state["memory_arn"]},
        {"Effect": "Allow", "Action": ["scheduler:CreateSchedule", "scheduler:UpdateSchedule", "scheduler:GetSchedule", "scheduler:DeleteSchedule"], "Resource": f"arn:aws:scheduler:{region}:{account_id}:schedule/mom-life/*"},
    ]
    if environment.get("MOM_LIFE_AUTOMATION_ROLE_ARN"):
        task_statements.append({"Effect": "Allow", "Action": "iam:PassRole", "Resource": environment["MOM_LIFE_AUTOMATION_ROLE_ARN"], "Condition": {"StringEquals": {"iam:PassedToService": "scheduler.amazonaws.com"}}})
    iam.put_role_policy(RoleName=task["RoleName"], PolicyName="mom-life-control-plane", PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": task_statements}))
    logs = session.client("logs")
    try:
        logs.create_log_group(logGroupName="/ecs/mom-life-backend", tags={"Project": NAME})
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    ecs = session.client("ecs")
    cluster_arn = ecs.create_cluster(clusterName="mom-life", tags=[{"key": "Project", "value": NAME}])["cluster"]["clusterArn"]
    secret_environment = json.loads(session.client("secretsmanager").get_secret_value(SecretId=state["config_secret_arn"])["SecretString"])
    secret_keys = [key for key in secret_environment if key not in {"MOM_LIFE_AWS_PROFILE", "MOM_LIFE_AGENTCORE_RUNTIME_ARN", "MOM_LIFE_AGENTCORE_MEMORY_ID"}]
    task_definition = ecs.register_task_definition(
        family="mom-life-backend", taskRoleArn=task["Arn"], executionRoleArn=execution["Arn"], networkMode="awsvpc", requiresCompatibilities=["FARGATE"], cpu="512", memory="1024", runtimePlatform={"cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX"},
        containerDefinitions=[{"name": "api", "image": f"{repository}:{args.image_tag}", "essential": True, "portMappings": [{"containerPort": 8000, "protocol": "tcp", "name": "http"}], "environment": [{"name": "MOM_LIFE_AGENTCORE_RUNTIME_ARN", "value": state["runtime_arn"]}, {"name": "MOM_LIFE_AGENTCORE_MEMORY_ID", "value": state["memory_id"]}], "secrets": [{"name": key, "valueFrom": f"{state['config_secret_arn']}:{key}::"} for key in secret_keys], "logConfiguration": {"logDriver": "awslogs", "options": {"awslogs-group": "/ecs/mom-life-backend", "awslogs-region": region, "awslogs-stream-prefix": "api"}}}],
        tags=[{"key": "Project", "value": NAME}],
    )["taskDefinition"]["taskDefinitionArn"]
    ec2 = session.client("ec2")
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc["VpcId"]]}, {"Name": "map-public-ip-on-launch", "Values": ["true"]}])["Subnets"]
    public_subnets = [item["SubnetId"] for item in sorted(subnets, key=lambda item: item["AvailabilityZone"])[:3]]
    alb_dns, target_group, task_group = ensure_load_balancer(session, vpc["VpcId"], public_subnets)
    database = session.client("rds").describe_db_instances(DBInstanceIdentifier="mom-life")["DBInstances"][0]
    database_group = database["VpcSecurityGroups"][0]["VpcSecurityGroupId"]
    allow(ec2, database_group, {"IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432, "UserIdGroupPairs": [{"GroupId": task_group, "Description": "mom.life ECS backend"}]})
    services = ecs.list_services(cluster=cluster_arn, launchType="FARGATE")["serviceArns"]
    existing_service = next((arn for arn in services if arn.rsplit("/", 1)[-1] == "mom-life-backend"), None)
    network = {"awsvpcConfiguration": {"subnets": public_subnets, "securityGroups": [task_group], "assignPublicIp": "ENABLED"}}
    if existing_service:
        ecs.update_service(cluster=cluster_arn, service="mom-life-backend", taskDefinition=task_definition, desiredCount=1, forceNewDeployment=True, healthCheckGracePeriodSeconds=120, deploymentConfiguration={"minimumHealthyPercent": 100, "maximumPercent": 200})
    else:
        ecs.create_service(cluster=cluster_arn, serviceName="mom-life-backend", taskDefinition=task_definition, desiredCount=1, launchType="FARGATE", platformVersion="LATEST", networkConfiguration=network, loadBalancers=[{"targetGroupArn": target_group, "containerName": "api", "containerPort": 8000}], healthCheckGracePeriodSeconds=120, deploymentConfiguration={"minimumHealthyPercent": 100, "maximumPercent": 200}, tags=[{"key": "Project", "value": NAME}], enableExecuteCommand=False)
    distribution_id, backend_domain, distribution_status = ensure_distribution(session.client("cloudfront"), alb_dns)
    state.update({"backend_repository": repository, "backend_image_tag": args.image_tag, "ecs_cluster": cluster_arn, "ecs_service": "mom-life-backend", "task_definition": task_definition, "alb_dns": alb_dns, "cloudfront_distribution_id": distribution_id, "backend_domain": backend_domain, "backend_url": f"https://{backend_domain}", "cloudfront_status": distribution_status})
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({key: state[key] for key in ("backend_repository", "task_definition", "backend_url", "cloudfront_status")}, indent=2))


if __name__ == "__main__":
    main()
