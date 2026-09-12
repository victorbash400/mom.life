"""Provision a private AWS scheduler dispatcher. Never starts application servers.
Run with PYTHONPATH=backend using an authenticated provisioning AWS profile.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import boto3

from app.automation_store import AutomationStore
from app.config import get_settings
from app.task_store import TaskStore


def template(secret_arn, subnets, security_groups, vpc_id, vpc_cidr):
    return {
        'AWSTemplateFormatVersion':'2010-09-09',
        'Resources':{
            'DispatcherGroup':{'Type':'AWS::EC2::SecurityGroup','Properties':{
                'GroupDescription':'mom.life automation dispatcher','VpcId':vpc_id,
                'SecurityGroupEgress':[
                    {'IpProtocol':'tcp','FromPort':5432,'ToPort':5432,'DestinationSecurityGroupId':security_groups[0]},
                    {'IpProtocol':'tcp','FromPort':443,'ToPort':443,'CidrIp':vpc_cidr}]}},
            'DatabaseIngress':{'Type':'AWS::EC2::SecurityGroupIngress','Properties':{
                'GroupId':security_groups[0],'IpProtocol':'tcp','FromPort':5432,'ToPort':5432,
                'SourceSecurityGroupId':{'Ref':'DispatcherGroup'}}},
            'EndpointIngress':{'Type':'AWS::EC2::SecurityGroupIngress','Properties':{
                'GroupId':{'Ref':'DispatcherGroup'},'IpProtocol':'tcp','FromPort':443,'ToPort':443,
                'SourceSecurityGroupId':{'Ref':'DispatcherGroup'}}},
            'SecretsEndpoint':{'Type':'AWS::EC2::VPCEndpoint','Properties':{
                'VpcId':vpc_id,'VpcEndpointType':'Interface','PrivateDnsEnabled':False,
                'ServiceName':{'Fn::Sub':'com.amazonaws.${AWS::Region}.secretsmanager'},
                'SubnetIds':[subnets[0]],'SecurityGroupIds':[{'Ref':'DispatcherGroup'}]}},
            'Group':{'Type':'AWS::Scheduler::ScheduleGroup','Properties':{'Name':'mom-life'}},
            'Failures':{'Type':'AWS::SQS::Queue','Properties':{'QueueName':'mom-life-automation-failures','MessageRetentionPeriod':1209600}},
            'DispatcherRole':{'Type':'AWS::IAM::Role','Properties':{
                'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'lambda.amazonaws.com'},'Action':'sts:AssumeRole'}]},
                'ManagedPolicyArns':['arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole'],
                'Policies':[{'PolicyName':'database-secret','PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'secretsmanager:GetSecretValue','Resource':secret_arn},
                    {'Effect':'Allow','Action':'sqs:SendMessage','Resource':{'Fn::GetAtt':['Failures','Arn']}}]}}]}},
            'Dispatcher':{'Type':'AWS::Lambda::Function','DependsOn':['DatabaseIngress','EndpointIngress','SecretsEndpoint'],'Properties':{
                'FunctionName':'mom-life-automation-dispatcher','Runtime':'python3.12','Handler':'handler.handler',
                'Role':{'Fn::GetAtt':['DispatcherRole','Arn']},'Timeout':30,'MemorySize':128,
                'VpcConfig':{'SubnetIds':subnets,'SecurityGroupIds':[{'Ref':'DispatcherGroup'}]},
                'Environment':{'Variables':{'DATABASE_SECRET_ARN':secret_arn,
                    'SECRETS_ENDPOINT_URL':{'Fn::Join':['',['https://',{'Fn::Select':[1,{'Fn::Split':[':',{'Fn::Select':[0,{'Fn::GetAtt':['SecretsEndpoint','DnsEntries']}]}]}]}]]}}},
                'Code':{'ZipFile':"def handler(event, context):\n    raise RuntimeError('Dispatcher package has not been installed')"}}},
            'AsyncDelivery':{'Type':'AWS::Lambda::EventInvokeConfig','Properties':{
                'FunctionName':{'Ref':'Dispatcher'},'Qualifier':'$LATEST','MaximumEventAgeInSeconds':21600,
                'MaximumRetryAttempts':2,'DestinationConfig':{'OnFailure':{'Destination':{'Fn::GetAtt':['Failures','Arn']}}}}},
            'SchedulerRole':{'Type':'AWS::IAM::Role','Properties':{
                'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'scheduler.amazonaws.com'},'Action':'sts:AssumeRole',
                    'Condition':{'StringEquals':{'aws:SourceAccount':{'Ref':'AWS::AccountId'}},'ArnEquals':{'aws:SourceArn':{'Fn::GetAtt':['Group','Arn']}}}}]},
                'Policies':[{'PolicyName':'deliver-automation-wake','PolicyDocument':{'Version':'2012-10-17','Statement':[
                    {'Effect':'Allow','Action':'lambda:InvokeFunction','Resource':{'Fn::GetAtt':['Dispatcher','Arn']}},
                    {'Effect':'Allow','Action':'sqs:SendMessage','Resource':{'Fn::GetAtt':['Failures','Arn']}}]}}]}}
        },
        'Outputs':{
            'TargetArn':{'Value':{'Fn::GetAtt':['Dispatcher','Arn']}},
            'RoleArn':{'Value':{'Fn::GetAtt':['SchedulerRole','Arn']}},
            'DeadLetterArn':{'Value':{'Fn::GetAtt':['Failures','Arn']}}
        }
    }


def package():
    with tempfile.TemporaryDirectory(prefix='mom-life-dispatcher-') as root:
        directory = Path(root)
        subprocess.run([sys.executable,'-m','pip','install','--platform','manylinux2014_x86_64',
                        '--implementation','cp','--python-version','3.12','--abi','cp312','--only-binary=:all:',
                        '--target',root,'psycopg[binary]','typing_extensions'],check=True)
        (directory/'handler.py').write_bytes((Path(__file__).resolve().parents[1]/'automation_lambda/handler.py').read_bytes())
        (directory/'rds-ca.pem').write_bytes((Path(__file__).resolve().parents[1]/'automation_lambda/rds-ca.pem').read_bytes())
        archive = directory/'dispatcher.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
            for path in directory.rglob('*'):
                if path.is_file() and path != archive and '__pycache__' not in path.parts:
                    output.write(path,path.relative_to(directory))
        return archive.read_bytes()


def provision(profile, subnets, security_groups):
    settings = get_settings()
    aws = boto3.Session(profile_name=profile,region_name=settings.strands_region)
    # Verify identity and deployment permission before writing a secret or creating resources.
    aws.client('sts').get_caller_identity()
    cloud = aws.client('cloudformation')
    cloud.list_stacks(StackStatusFilter=['CREATE_COMPLETE','UPDATE_COMPLETE'])
    AutomationStore(TaskStore(settings.database_url)).initialize()
    secrets = aws.client('secretsmanager')
    try:
        secret_arn = secrets.create_secret(Name='mom-life/automation-database',SecretString=settings.database_url)['ARN']
    except secrets.exceptions.ResourceExistsException:
        secret_arn = secrets.describe_secret(SecretId='mom-life/automation-database')['ARN']
        secrets.put_secret_value(SecretId=secret_arn,SecretString=settings.database_url)
    network = aws.client('ec2')
    vpc_id = network.describe_subnets(SubnetIds=subnets)['Subnets'][0]['VpcId']
    vpc_cidr = network.describe_vpcs(VpcIds=[vpc_id])['Vpcs'][0]['CidrBlock']
    body = json.dumps(template(secret_arn,subnets,security_groups,vpc_id,vpc_cidr))
    name = 'mom-life-automations'
    try:
        cloud.create_stack(StackName=name,TemplateBody=body,Capabilities=['CAPABILITY_IAM'])
        # Waiters are intentionally left to a separate invocation; no provisioning polling loop.
        print('Stack creation submitted. After it completes, run again to install the dispatcher.')
        return
    except cloud.exceptions.AlreadyExistsException:
        stack = cloud.describe_stacks(StackName=name)['Stacks'][0]
        if stack['StackStatus'] not in {'CREATE_COMPLETE','UPDATE_COMPLETE'}:
            raise RuntimeError(f"Automation stack is {stack['StackStatus']}; inspect CloudFormation before continuing.")
    try:
        cloud.update_stack(StackName=name,TemplateBody=body,Capabilities=['CAPABILITY_IAM'])
        print('Stack update submitted. After it completes, run again to install the dispatcher.')
        return
    except cloud.exceptions.ClientError as error:
        if 'No updates are to be performed' not in str(error):
            raise
    outputs = {item['OutputKey']:item['OutputValue'] for item in stack['Outputs']}
    aws.client('lambda').update_function_code(FunctionName='mom-life-automation-dispatcher',ZipFile=package())
    group_arn = f"arn:aws:scheduler:{settings.strands_region}:{aws.client('sts').get_caller_identity()['Account']}:schedule/mom-life/*"
    policy = {'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':['scheduler:CreateSchedule','scheduler:UpdateSchedule','scheduler:DeleteSchedule','scheduler:GetSchedule'],'Resource':group_arn},
        {'Effect':'Allow','Action':'iam:PassRole','Resource':outputs['RoleArn'],'Condition':{'StringEquals':{'iam:PassedToService':'scheduler.amazonaws.com'}}}]}
    aws.client('iam').put_user_policy(UserName='mom-life-app',PolicyName='mom-life-automations',PolicyDocument=json.dumps(policy))
    environment = Path(__file__).resolve().parents[1]/'.env'
    replacements = {'MOM_LIFE_AUTOMATION_TARGET_ARN':outputs['TargetArn'],'MOM_LIFE_AUTOMATION_ROLE_ARN':outputs['RoleArn'],'MOM_LIFE_AUTOMATION_DLQ_ARN':outputs['DeadLetterArn']}
    lines = environment.read_text().splitlines()
    lines = [line for line in lines if line.split('=',1)[0] not in replacements]
    environment.write_text('\n'.join([*lines,*[f'{key}={value}' for key,value in replacements.items()]])+'\n')
    print('Dispatcher code submitted and scheduler configuration saved. Verify Lambda update completion and a test wake before enabling real schedules.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile',default='operator-provisioning')
    parser.add_argument('--subnet-ids',nargs='+',required=True)
    parser.add_argument('--security-group-ids',nargs='+',required=True)
    args = parser.parse_args()
    provision(args.profile,args.subnet_ids,args.security_group_ids)
