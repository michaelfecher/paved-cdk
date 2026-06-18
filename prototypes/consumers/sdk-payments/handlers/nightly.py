from paved_cdk.sdk import scheduled


@scheduled("rate(1 day)", memory=512)
def nightly(event, context):
    return {"generated": True}
