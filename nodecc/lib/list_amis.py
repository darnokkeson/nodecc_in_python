from .client import get_ec2


def list_amis():
    """Return Amazon Linux 2 AMIs as {'ami_ids': [...], 'descriptions': [...]}."""
    ec2 = get_ec2()
    data = ec2.describe_images(
        Filters=[
            {
                "Name": "name",
                "Values": ["amzn2-ami-hvm-2.0.202*-x86_64-gp2"],
            },
        ],
    )
    images = data.get("Images", [])
    return {
        "ami_ids": [image["ImageId"] for image in images],
        "descriptions": [image.get("Description", "") for image in images],
    }
