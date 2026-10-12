from .client import get_ec2


def list_subnets():
    """Return the subnet ids of the default VPC."""
    ec2 = get_ec2()
    vpcs = ec2.describe_vpcs(
        Filters=[
            {
                "Name": "isDefault",
                "Values": ["true"],
            },
        ],
    )
    vpc_id = vpcs["Vpcs"][0]["VpcId"]
    data = ec2.describe_subnets(
        Filters=[
            {
                "Name": "vpc-id",
                "Values": [vpc_id],
            },
        ],
    )
    return [subnet["SubnetId"] for subnet in data.get("Subnets", [])]
