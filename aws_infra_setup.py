import boto3
import botocore.exceptions
import time

# Step 1: Check if S3 Bucket Exists


def check_bucket_exists(bucket_name, region='us-east-2'):
    s3 = boto3.client('s3', region_name=region)
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists in {region}.")
        return True
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            return False
        elif error_code == 403:
            print(f"Bucket {bucket_name} exists but is not owned by you.")
            return True
        else:
            print(f"Unexpected error: {e}")
            return False

# Step 2: Create S3 Bucket


def create_s3_bucket(bucket_name, region='us-east-2'):
    print(f"Creating S3 bucket in region: {region}")
    s3 = boto3.client('s3', region_name=region)
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"S3 bucket {bucket_name} created successfully in {region}.")
    except botocore.exceptions.ClientError as e:
        print(f"Error creating bucket: {e.response['Error']['Message']}")

# Step 3: Launch EC2 Instance with Nginx


def launch_ec2_instance(key_name, security_group_id):
    print("Launching EC2 instance with Nginx...")
    ec2 = boto3.resource('ec2', region_name='us-east-2')
    instance = ec2.create_instances(
        ImageId='ami-0c55b159cbfafe1f0',  # Amazon Linux 2 AMI
        InstanceType='t2.micro',
        KeyName=key_name,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group_id],
        UserData="""#!/bin/bash
        yum update -y
        amazon-linux-extras enable nginx1
        yum install -y nginx
        systemctl start nginx
        systemctl enable nginx
        echo '<h1>Nginx Web Application Deployed</h1>' > /usr/share/nginx/html/index.html
        """
    )
    instance_id = instance[0].id
    print(f"EC2 Instance {instance_id} launched.")
    return instance_id

# Step 4: Create Application Load Balancer


def create_load_balancer(subnets, security_group_id):
    print("Creating Load Balancer...")
    elb = boto3.client('/=2', region_name='us-east-2')
    load_balancer = elb.create_load_balancer(
        Name='my-alb',
        Subnets=subnets,
        SecurityGroups=[security_group_id],
        Type='application',
        IpAddressType='ipv4'
    )
    alb_dns_name = load_balancer['LoadBalancers'][0]['DNSName']
    print(f"Load Balancer created with DNS: {alb_dns_name}")
    return load_balancer['LoadBalancers'][0]['LoadBalancerArn']

# Step 5: Create Target Group for Load Balancer


def create_target_group(vpc_id):
    print("Creating Target Group...")
    elb = boto3.client('elbv2', region_name='us-east-2')
    target_group_name = "my-targets"
    try:
        target_group = elb.create_target_group(
            Name=target_group_name,
            Protocol='HTTP',
            Port=80,
            VpcId=vpc_id,
            HealthCheckProtocol='HTTP',
            HealthCheckPath='/',
            TargetType='instance'
        )
        target_group_arn = target_group['TargetGroups'][0]['TargetGroupArn']
        print(f"Target Group created with ARN: {target_group_arn}")
        return target_group_arn
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'DuplicateTargetGroupName':
            print("Target group with this name already exists. Retrieving existing ARN...")
            existing_groups = elb.describe_target_groups(Names=[target_group_name])
            return existing_groups['TargetGroups'][0]['TargetGroupArn']
        else:
            raise

# Step 6: Register EC2 Instances with Load Balancer


def register_ec2_with_alb(target_group_arn, instance_id):
    print("Registering EC2 instance with Load Balancer...")
    elb = boto3.client('elbv2', region_name='us-east-2')
    elb.register_targets(
        TargetGroupArn=target_group_arn,
        Targets=[{'Id': instance_id}]
    )
    print("EC2 instance registered with Load Balancer.")

# Main Workflow


def main():
    bucket_name = "my-web-app-bucket-unique12345"  # Replace with a unique bucket name
    key_name = "my-new-key"
    security_group_id = "sg-0d65baf275e4e7138"
    subnets = ["subnet-0cb3ff7ef16c46b62", "subnet-00d74ea96628467ec"]
    vpc_id = "vpc-0a6e1fef7753a3f66"  # Replace with your VPC ID
    target_group_arn = "arn:aws:elasticloadbalancing:us-east-2:225989348530:targetgroup/my-targets/451a31192b5daa75"


    # Step 1: Check if S3 bucket exists
    if not check_bucket_exists(bucket_name, region='us-east-2'):
        # Step 2: Create S3 bucket if it doesn't exist
        create_s3_bucket(bucket_name, region='us-east-2')

    # Step 3: Launch EC2 instance with Nginx
    instance_id = launch_ec2_instance(key_name, security_group_id)
    time.sleep(10)  # Wait for the instance to initialize

    # Step 4: Create Load Balancer
    
    
    alb_arn = create_load_balancer(subnets, security_group_id)

    # Step 5: Create Target Group
    target_group_arn = create_target_group(vpc_id)

    # Step 6: Register EC2 instance with Load Balancer
    register_ec2_with_alb(target_group_arn, instance_id)

    print("Web application setup complete.")


if __name__ == "__main__":
    main()
