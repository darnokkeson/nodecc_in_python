from .client import get_ec2


def terminate_vm(instance_id):
    """Terminate a single instance."""
    ec2 = get_ec2()
    ec2.terminate_instances(InstanceIds=[instance_id])
