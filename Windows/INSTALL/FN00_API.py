import boto3
import json
import base64

def lambda_handler(event, context):
    # Check for queryString
    TestParam = event.get("queryStringParameters", False)

    if TestParam:
        # Check for hostname queryString
        if "hostname" in event["queryStringParameters"]:
            ImageBuilderHostname = event["queryStringParameters"]["hostname"]
        else:
            return {"statusCode": 400, "body": json.dumps("Invalid parameter.")}
    else:
        return {"statusCode": 400, "body": json.dumps("Invalid parameter.")}

    # Get local password from parameter store
    try:
        SSMParameterName = "/wks_automation/" + ImageBuilderHostname
        ssm_client = boto3.client("ssm")
        response = ssm_client.get_parameter(Name=SSMParameterName, WithDecryption=True)

        ImageBuilderPassword = response["Parameter"]["Value"]
        encodedPassword = base64.b64encode(ImageBuilderPassword.encode("utf-8"))

        response = encodedPassword
    except Exception:
        return {"statusCode": 400, "body": json.dumps("Invalid parameter.")}

    return {"statusCode": 200, "body": json.dumps(response)}
