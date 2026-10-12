from .client import get_ec2


def show_vm(instance_id):
    """Return the full instance record for a single instance id."""
    ec2 = get_ec2()
    data = ec2.describe_instances(InstanceIds=[instance_id])
    return data["Reservations"][0]["Instances"][0]
