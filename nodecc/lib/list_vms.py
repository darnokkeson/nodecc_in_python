from .client import get_ec2


def list_vms():
    """Return the ids of all pending or running instances (max 10)."""
    ec2 = get_ec2()
    data = ec2.describe_instances(
        Filters=[
            {
                "Name": "instance-state-name",
                "Values": ["pending", "running"],
            },
        ],
        MaxResults=10,
    )
    instance_ids = []
    for reservation in data.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_ids.append(instance["InstanceId"])
    return instance_ids
