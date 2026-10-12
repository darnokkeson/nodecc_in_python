from .client import get_ec2


def create_vm(ami_id, subnet_id):
    """Launch a single t3.micro instance in the given subnet."""
    ec2 = get_ec2()
    ec2.run_instances(
        IamInstanceProfile={"Name": "ec2-ssm-core"},
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType="t3.micro",
        SubnetId=subnet_id,
    )
