import boto3
import subprocess
import json
from botocore.exceptions import ClientError

# AWS resource names
REGION = 'us-east-1'  # Change if needed
REPO_NAME = 'ucc-benchmark-repo'  # ECR repository name
CLUSTER_NAME = 'ucc-cluster'  # ECS Cluster name
TASK_DEFINITION_NAME = 'ucc-benchmark-task'  # ECS task definition name

# Create AWS clients
ecr_client = boto3.client('ecr', region_name=REGION)
iam_client = boto3.client('iam', region_name=REGION)
ecs_client = boto3.client('ecs', region_name=REGION)
ec2_client = boto3.client('ec2', region_name=REGION)

# Ensure IAM roles exist (task role and execution role)
def ensure_roles_exist():
    try:
        # Check if ecsTaskRole exists
        task_role = iam_client.get_role(RoleName='ecsTaskRole')
        task_role_arn = task_role['Role']['Arn']
    except iam_client.exceptions.NoSuchEntityException:
        # Create ecsTaskRole if it doesn't exist
        task_role = iam_client.create_role(
            RoleName='ecsTaskRole',
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "ecs-tasks.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            })
        )
        task_role_arn = task_role['Role']['Arn']
        iam_client.attach_role_policy(
            RoleName='ecsTaskRole',
            PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonECSTaskRolePolicy'
        )
    
    try:
        # Check if ecsTaskExecutionRole exists
        execution_role = iam_client.get_role(RoleName='ecsTaskExecutionRole')
        execution_role_arn = execution_role['Role']['Arn']
    except iam_client.exceptions.NoSuchEntityException:
        # Create ecsTaskExecutionRole if it doesn't exist
        execution_role = iam_client.create_role(
            RoleName='ecsTaskExecutionRole',
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "ecs-tasks.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            })
        )
        execution_role_arn = execution_role['Role']['Arn']
        iam_client.attach_role_policy(
            RoleName='ecsTaskExecutionRole',
            PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'
        )
    
    return task_role_arn, execution_role_arn

# Ensure ECR repository exists
def ensure_ecr_repository_exists(repo_name):
    try:
        response = ecr_client.describe_repositories(repositoryNames=[repo_name])
        repository_uri = response['repositories'][0]['repositoryUri']
    except ecr_client.exceptions.RepositoryNotFoundException:
        # Create ECR repository if it doesn't exist
        response = ecr_client.create_repository(repositoryName=repo_name)
        repository_uri = response['repository']['repositoryUri']
    return repository_uri

# Push Docker image to ECR
def push_docker_image_to_ecr(repository_uri):
    try:
        # Build the Docker image using the Dockerfile in "../../"
        # subprocess.run(["docker", "build", "-t", repository_uri, "../../"], check=True)

        # Authenticate Docker to the ECR repository
        login_password = subprocess.run(
            ["aws", "ecr", "get-login-password", "--region", REGION],
            stdout=subprocess.PIPE,
            check=True
        ).stdout.decode('utf-8')  # Decode bytes to string

        subprocess.run(
            ["docker", "login", "--username", "AWS", "--password-stdin", repository_uri],
            input=login_password,
            text=True,  # Use text=True for string input
            check=True
        )

        # Tag the Docker image
        subprocess.run(["docker", "tag", repository_uri, f"{repository_uri}:latest"], check=True)

        # Push the Docker image to ECR
        subprocess.run(["docker", "push", f"{repository_uri}:latest"], check=True)

        print(f"Successfully pushed Docker image to {repository_uri}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during Docker operations: {e}")
        raise

# Generate ECS task definition JSON
def generate_task_def(task_role_arn, execution_role_arn, image_url):
    task_definition = {
        "family": TASK_DEFINITION_NAME,
        "executionRoleArn": execution_role_arn,
        "taskRoleArn": task_role_arn,
        "networkMode": "awsvpc",
        "containerDefinitions": [
            {
                "name": "ucc-benchmark-container",
                "image": image_url,
                "essential": True,
                "memory": 1024,
                "cpu": 512,
                "environment": [],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/ucc-benchmark",
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": "ecs"
                    }
                }
            }
        ]
    }
    
    with open('task-def.json', 'w') as f:
        json.dump(task_definition, f, indent=4)

# Register ECS task definition
def register_task_definition():
    with open('task-def.json', 'r') as f:
        task_definition = json.load(f)
    
    response = ecs_client.register_task_definition(**task_definition)
    return response['taskDefinition']['taskDefinitionArn']

# Ensure the ECS cluster exists, create if it doesn't
def ensure_cluster_exists(cluster_name):
    clusters = ecs_client.list_clusters()["clusterArns"]
    for cluster in clusters:
        if cluster_name in cluster:
            print(f"Cluster {cluster_name} exists.")
            return
    print(f"Cluster {cluster_name} not found. Creating...")
    ecs_client.create_cluster(clusterName=cluster_name)
    print(f"Cluster {cluster_name} created.")

# Create a new security group
def create_security_group(vpc_id):
    try:
        sg_response = ec2_client.create_security_group(
            GroupName="ucc-benchmark-sg",
            Description="Security group for UCC benchmarks",
            VpcId=vpc_id,
        )
        sg_id = sg_response['GroupId']
        print(f"Created Security Group: {sg_id}")
        
        # Allow inbound and outbound traffic to/from all IPs
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]
        )
        ec2_client.authorize_security_group_egress(
            GroupId=sg_id,
            IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]
        )
        return sg_id
    except ClientError as e:
        print(f"Error creating security group: {e}")
        raise

def ensure_vpc_exists():
    # Check if there are existing VPCs
    vpcs = ec2_client.describe_vpcs()["Vpcs"]
    
    if len(vpcs) > 0:
        # Use the first VPC found
        vpc_id = vpcs[0]["VpcId"]
        print(f"Using existing VPC {vpc_id}")
    else:
        # If no VPC exists, create a new one
        print("No existing VPC found. Creating a new VPC...")
        vpc_response = ec2_client.create_vpc(
            CidrBlock='10.0.0.0/16',  # Example CIDR block, adjust if needed
            AmazonProvidedIpv6CidrBlock=True  # Enable IPv6 if required
        )
        vpc_id = vpc_response['Vpc']['VpcId']
        print(f"Created new VPC with ID {vpc_id}")

        # Optionally, enable DNS support and DNS hostnames for the VPC
        ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
        ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})

    return vpc_id

def get_subnet_id(vpc_id):
    # Describe subnets to get the subnet ID for the given VPC
    subnets = ec2_client.describe_subnets(Filters=[{
        'Name': 'vpc-id',
        'Values': [vpc_id]
    }])['Subnets']

    if subnets:
        # Return the first subnet ID (you can modify to return a specific subnet if necessary)
        subnet_id = subnets[0]['SubnetId']
        print(f"Found subnet {subnet_id} in VPC {vpc_id}")
        return subnet_id
    else:
        raise Exception(f"No subnets found in VPC {vpc_id}")


# Run ECS task
def run_task(task_definition_arn, security_group_id, subnet_id):
    response = ecs_client.run_task(
        cluster=CLUSTER_NAME,
        taskDefinition=task_definition_arn,
        count=1,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [subnet_id],  # Replace with actual subnet ID
                "securityGroups": [security_group_id],  # Use created security group
                "assignPublicIp": "ENABLED"
            }
        }
    )
    print("Task is running with ARN:", response['tasks'][0]['taskArn'])

if __name__ == "__main__":
    # Ensure IAM roles exist
    task_role_arn, execution_role_arn = ensure_roles_exist()

    # Ensure ECR repository exists and get the repository URI
    repository_uri = ensure_ecr_repository_exists(REPO_NAME)

    # Push the Docker image to ECR
    push_docker_image_to_ecr(repository_uri)

    # Generate task definition JSON with the ECR image URL
    image_url = f"{repository_uri}:latest"
    generate_task_def(task_role_arn, execution_role_arn, image_url)

    # Register the task definition
    task_definition_arn = register_task_definition()

    # Ensure the cluster exists before running tasks
    ensure_cluster_exists(CLUSTER_NAME)

    # Ensure VPC exists
    vpc_id = ensure_vpc_exists()

    # Get subnet ID for the VPC
    subnet_id = get_subnet_id(vpc_id)

    # Create a security group and retrieve its ID
    security_group_id = create_security_group(vpc_id)

    # Run the task on ECS
    run_task(task_definition_arn, security_group_id, subnet_id)  