import os

# Mirror the Node app (AWS_SDK_LOAD_CONFIG=1) so the shared AWS config file
# (~/.aws/config) is honoured when resolving credentials and defaults.
os.environ.setdefault("AWS_SDK_LOAD_CONFIG", "1")

import boto3

REGION = "us-east-1"

_client = None


def get_ec2():
    """Return a shared EC2 client for the fixed region used by the app."""
    global _client
    if _client is None:
        _client = boto3.client("ec2", region_name=REGION)
    return _client
