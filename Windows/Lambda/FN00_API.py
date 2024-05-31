# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import boto3
import json
import base64
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # Check for queryString
    logger.info("Obtaining queryStringParameters in event data.")
    TestParam = event.get("queryStringParameters", False)

    if TestParam:
        # Check for hostname queryString
        logger.info("Checking for hostname in queryString.")
        if "hostname" in event["queryStringParameters"]:
            ImageBuilderHostname = event["queryStringParameters"]["hostname"]
            logger.info("Hostname found, %s", ImageBuilderHostname)
        else:
            logger.error("Hostname not found in queryString.")
            return {"statusCode": 400, "body": json.dumps("Invalid parameter.")}
    else:
        logger.error("No queryStringParameters found in event data.")
        return {"statusCode": 400, "body": json.dumps("Invalid parameter.")}

    # Get local password from parameter store
    try:
        logger.info("Retreiving information for %s from parameter store.", ImageBuilderHostname)
        SSMParameterName = "/wks_automation/" + ImageBuilderHostname
        ssm_client = boto3.client("ssm")
        response = ssm_client.get_parameter(Name=SSMParameterName, WithDecryption=True)

        ImageBuilderPassword = response["Parameter"]["Value"]
        encodedPassword = base64.b64encode(ImageBuilderPassword.encode("utf-8"))

        response = encodedPassword
        logger.info("Successfully obtained infromation from parameter store. Response sent.")
    except Exception:
        logger.error("Unable to retreive information from parameter store.")
        return {"statusCode": 400, "body": json.dumps("Invalid parameter.")}

    return {"statusCode": 200, "body": response}
