from paved_cdk.sdk import api


@api.post("/charge")
def charge(event, context):
    return {"statusCode": 200, "body": "charged"}
