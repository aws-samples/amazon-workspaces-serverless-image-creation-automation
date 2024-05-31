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

import logging
import boto3
import winrm

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # Retrieve image builder hostname from event data
    logger.info(
        "Querying for image builder WorkSpace IP address and hostname in event data."
    )
    try:
        ImageBuilderIPAddress = event["ImageBuilderStatus"]["Workspaces"][0][
            "IpAddress"
        ]
        ImageBuilderHostname = event["ImageBuilderStatus"]["Workspaces"][0][
            "ComputerName"
        ]
        logger.info(
            "IP address for %s found: %s.", ImageBuilderHostname, ImageBuilderIPAddress
        )
    except Exception as e:
        logger.error(e)
        logger.info(
            "Unable to find IP address or hostname for image builder WorkSpace."
        )

    # Retrieve image description from event data
    logger.info("Querying for image description in event data.")
    try:
        ImageDescription = event["AutomationParameters"]["ImageDescription"]
        logger.info("Description found: %s.", ImageDescription)
    except Exception as e:
        logger.error(e)
        logger.info("Unable to find image description.")

    # Update image description to include base bundle id and operating system if left at default
    if ImageDescription == "Default":
        logger.info(
            "Default image description detected, updating with relevant information."
        )
        ImageBuilderBundleId = event["ImageBuilderStatus"]["Workspaces"][0]["BundleId"]
        ImageBuilderOS = event["ImageBuilderStatus"]["Workspaces"][0][
            "WorkspaceProperties"
        ]["OperatingSystemName"]
        ImageDescription = (
            "Image created by WorkSpaces automation pipeline. Built on the starting bundle "
            + ImageBuilderBundleId
            + " running "
            + ImageBuilderOS
            + "."
        )
    else:
        logger.info("Custom image description detected, keeping intact.")

    # Retrieve image builder temporary password from parameter store
    logger.info(
        "Retreiving local admin password for image builder WorkSpace from parameter store."
    )
    try:
        ImageBuilderUser = "wks_automation"
        SSMParameterName = "/wks_automation/" + ImageBuilderHostname
        ssm_client = boto3.client("ssm")
        response = ssm_client.get_parameter(Name=SSMParameterName, WithDecryption=True)
        ImageBuilderPassword = response["Parameter"]["Value"]
        logger.info("Retreival successful.")
    except Exception as e:
        logger.error(e)
        logger.info("Unable to retreive temporary admin password from parameter store.")

    try:
        # Connect to remote image builder WorkSpace using pywinrm library
        logger.info(
            "Connecting to host %s as user %s.", ImageBuilderIPAddress, ImageBuilderUser
        )
        session = winrm.Session(
            ImageBuilderIPAddress, auth=(ImageBuilderUser, ImageBuilderPassword)
        )
    except Exception as e2:
        logger.error(e2)

    logger.info("Cleanup PSUpdate Scheduled Task.")
    _result = session.run_ps(
        "Unregister-ScheduledTask -TaskName PSWindowsUpdate -Confirm:$false"
    )

    logger.info("Remove installation source files.")
    _result = session.run_cmd("rmdir /s/q C:\\wks_automation\\")

    logger.info("Removing temporary local admin information from parameter store.")
    SSMParameterName = "/wks_automation/" + ImageBuilderHostname
    try:
        ssm_client = boto3.client("ssm")
        response = ssm_client.delete_parameter(Name=SSMParameterName)
        logger.info("Parameter successfully removed.")
    except Exception as e:
        logger.error(e)
        logger.info("Unable to remove parameter.")

    # Retrieve DisableAPI from event data
    logger.info("Querying for DisableAPI in event data.")
    try:
        ImageBuilderAPI = event["AutomationParameters"]["ImageBuilderAPI"]
        DisableAPI = event["AutomationParameters"]["DisableAPI"]
        logger.info("The API, %s, will be disabled, %s.", ImageBuilderAPI, DisableAPI)
    except Exception as e:
        logger.error(e)
        logger.info("Unable to find DisableAPI in event data.")

    if DisableAPI:
        logger.info("Disabling API default endpoint now.")

        api_client = boto3.client("apigateway")
        # Disable default endpoint
        response = api_client.update_rest_api(
            restApiId=ImageBuilderAPI,
            patchOperations=[
                {
                    "op": "replace",
                    "path": "/disableExecuteApiEndpoint",
                    "value": "True",
                },
            ],
        )

        logger.info("API endpoint disabled, deploying API update.")
        # Deploy API changes
        response = api_client.create_deployment(
            restApiId=ImageBuilderAPI,
            stageName="prod",
        )
        logger.info(
            "API deploy complete, API will be unavailable in approx. 30 seconds."
        )

    return {"ImageDescription": ImageDescription}
