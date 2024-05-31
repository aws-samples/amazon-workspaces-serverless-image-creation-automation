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
import json
import textwrap

logger = logging.getLogger()
logger.setLevel(logging.INFO)

workspaces_client = boto3.client("workspaces")
sns_client = boto3.client("sns")


def lambda_handler(event, context):
    logger.info(
        "Beginning execution of WorkSpaces_Automation_Image_Notification function."
    )

    # Retrieve SNS topic ARN from event data
    if "ImageNotificationARN" in event["AutomationParameters"]:
        ImageNotificationARN = event["AutomationParameters"]["ImageNotificationARN"]
        logger.info(
            "ImageNotificationARN found found in event data: %s.", ImageNotificationARN
        )
    else:
        logger.info("ImageNotificationARN not found found in event data.")

    # Retrieve create bundle status
    if "CreateBundle" in event["AutomationParameters"]:
        CreateBundle = event["AutomationParameters"]["CreateBundle"]
    else:
        CreateBundle = False

    # Retrieve WorkSpaces image Id from event data
    ImageId = event["ImageStatus"]["Images"][0]["ImageId"]

    # Query status of WorkSpace image
    try:
        response = workspaces_client.describe_workspace_images(
            ImageIds=[
                ImageId,
            ]
        )
        logger.info("Image found, generating notification content.")

        # Pull required information from response
        ImageName = response["Images"][0]["Name"]
        ImagePlatform = response["Images"][0]["OperatingSystem"]["Type"]
        ImageState = response["Images"][0]["State"]
        ImageId = response["Images"][0]["ImageId"]

    except Exception as e:
        logger.error(e)
        logger.info("Unable to query status of image.")

    # Get errors from configuration routine
    try:
        InstallRoutineErrors = event["InstallRoutineRemaining"]["InstallRoutineErrors"]

        if not InstallRoutineErrors:
            # Empty list, no errors
            InstallRoutineErrorCount = 0
        elif "No routine provided." in InstallRoutineErrors[0]:
            InstallRoutineErrorCount = "No routine provided"
        else:
            InstallRoutineErrorCount = len(InstallRoutineErrors)

    except Exception as e:
        logger.error(e)
        logger.info("Unable to query for configuration routine errors.")
        InstallRoutineErrorCount = "No routine error list found"

    # Get AWS account number
    AccountId = boto3.client("sts").get_caller_identity()["Account"]

    # Get list of all parameters sent into the Lambda function from event
    FullOutput = json.dumps(event, indent=4, separators=(",", ": "), sort_keys=False)

    sbj = "WorkSpaces Image Creation Notification: {0}".format(ImageName)

    msg = textwrap.dedent(
        """\
        ------------------------------------------------------------------------------
        Image Information:
        ------------------------------------------------------------------------------
        Image Name:       {0}
        Image ID:             {1}
        Image Platform:   {2}
        Image Status:      {3}
        Config Errors:      {4}
        AWS Account:     {5}
        """
    ).format(
        ImageName,
        ImageId,
        ImagePlatform,
        ImageState,
        InstallRoutineErrorCount,
        AccountId,
    )

    if CreateBundle:
        logger.info("Bundle found, generating notification content.")

        BundleName = event["BundleStatus"]["WorkspaceBundle"]["Name"]
        BundleId = event["BundleStatus"]["WorkspaceBundle"]["BundleId"]
        BundleType = event["BundleStatus"]["WorkspaceBundle"]["ComputeType"]["Name"]
        RootSize = event["BundleStatus"]["WorkspaceBundle"]["RootStorage"]["Capacity"]
        UserSize = event["BundleStatus"]["WorkspaceBundle"]["UserStorage"]["Capacity"]

        msg = msg + textwrap.dedent(
            """\
            ------------------------------------------------------------------------------
            Bundle Information:
            ------------------------------------------------------------------------------
            Bundle Name:      {0}
            Bundle ID:            {1}
            Bundle Type:        {2}
            Root Vol. Size:     {3} GB
            User Vol. Size:     {4} GB
            """
        ).format(BundleName, BundleId, BundleType, RootSize, UserSize)

    msg = msg + textwrap.dedent(
        """\
        ------------------------------------------------------------------------------
        Full Pipeline Output:
        ------------------------------------------------------------------------------
        {0}
        """
    ).format(FullOutput)

    # Publish image information to SNS Topic
    try:
        response = sns_client.publish(
            TopicArn=ImageNotificationARN, Message=msg, Subject=sbj
        )

        MessageID = response["MessageId"]

        logger.info("Notification published to SNS topic.")

    except Exception as e2:
        logger.error(e2)
        MessageID = "Error"

    logger.info(
        "Completed WorkSpaces_Automation_Image_Notification function, returning MessageID to Step Function."
    )

    return MessageID
