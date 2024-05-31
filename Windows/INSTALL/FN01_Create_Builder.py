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
import os
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WorkspacesClient = boto3.client("workspaces")


def lambda_handler(event, context):
    logger.info(
        "Beginning execution of WorkSpaces_Automation_Windows_Create_Builder function."
    )

    # Retrieve starting parameters from event data
    # If parameter not found, inject default values defined in Lambda function
    if "ImageBuilderDirectory" in event:
        ImageBuilderDirectory = event["ImageBuilderDirectory"]
    else:
        ImageBuilderDirectory = os.environ["Default_DirectoryId"]

    if "ImageBuilderUser" in event:
        ImageBuilderUser = event["ImageBuilderUser"]
    else:
        ImageBuilderUser = os.environ["Default_WorkSpaceUser"]

    if "ImageBuilderBundleId" in event:
        ImageBuilderBundleId = event["ImageBuilderBundleId"]
    else:
        ImageBuilderBundleId = os.environ["Default_BundleId"]

    if "ImageBuilderComputeType" in event:
        ImageBuilderComputeType = event["ImageBuilderComputeType"]
    else:
        ImageBuilderComputeType = os.environ["Default_ComputeType"]

    if "ImageBuilderProtocol" in event:
        ImageBuilderProtocol = event["ImageBuilderProtocol"]
    else:
        ImageBuilderProtocol = os.environ["Default_Protocol"]

    if "ImageBuilderRootVolumeSize" in event:
        ImageBuilderRootVolumeSize = int(event["ImageBuilderRootVolumeSize"])
    else:
        ImageBuilderRootVolumeSize = int(os.environ["Default_RootVolumeSize"])

    if "ImageBuilderUserVolumeSize" in event:
        ImageBuilderUserVolumeSize = int(event["ImageBuilderUserVolumeSize"])
    else:
        ImageBuilderUserVolumeSize = int(os.environ["Default_UserVolumeSize"])

    if "ImageBuilderSecurityGroup" in event:
        ImageBuilderSecurityGroup = event["ImageBuilderSecurityGroup"]
    else:
        ImageBuilderSecurityGroup = os.environ["Default_SecurityGroup"]

    if "ImageNamePrefix" in event:
        ImageNamePrefix = event["ImageNamePrefix"]
    else:
        ImageNamePrefix = os.environ["Default_ImagePrefix"]

    if "ImageDescription" in event:
        ImageDescription = event["ImageDescription"]
    else:
        ImageDescription = "Default"

    if "DeleteBuilder" in event:
        DeleteBuilder = event["DeleteBuilder"]
    else:
        DeleteBuilder = True

    if "DisableAPI" in event:
        DisableAPI = event["DisableAPI"]
    else:
        DisableAPI = True

    if "ImageBuilderAPI" in event:
        ImageBuilderAPI = event["ImageBuilderAPI"]
    else:
        ImageBuilderAPI = os.environ["Default_APIId"]

    if "ImageTags" in event:
        ImageTags = event["ImageTags"]
    else:
        ImageTags = False

    if "ImageNotificationARN" in event:
        ImageNotificationARN = event["ImageNotificationARN"]
    else:
        ImageNotificationARN = os.environ["Default_NotificationARN"]

    if "CreateBundle" in event:
        CreateBundle = event["CreateBundle"]
    else:
        CreateBundle = False

    if "BundleNamePrefix" in event:
        BundleNamePrefix = event["BundleNamePrefix"]
    else:
        BundleNamePrefix = os.environ["Default_BundlePrefix"]

    if "BundleDescription" in event:
        BundleDescription = event["BundleDescription"]
    else:
        BundleDescription = "Created with automated pipeline"

    if "BundleComputeType" in event:
        BundleComputeType = event["BundleComputeType"]
    else:
        BundleComputeType = os.environ["Default_ComputeType"]

    if "BundleRootVolumeSize" in event:
        BundleRootVolumeSize = event["BundleRootVolumeSize"]
    else:
        BundleRootVolumeSize = os.environ["Default_RootVolumeSize"]

    if "BundleUserVolumeSize" in event:
        BundleUserVolumeSize = event["BundleUserVolumeSize"]
    else:
        BundleUserVolumeSize = os.environ["Default_UserVolumeSize"]

    if "BundleTags" in event:
        BundleTags = event["BundleTags"]
    else:
        BundleTags = False

    if "SoftwareS3Bucket" in event:
        SoftwareS3Bucket = event["SoftwareS3Bucket"]
    else:
        SoftwareS3Bucket = os.environ["Default_S3Bucket"]

    if "InstallRoutine" in event:
        InstallRoutine = event["InstallRoutine"]
    else:
        InstallRoutine = False

    if "SkipWindowsUpdates" in event:
        SkipWindowsUpdates = event["SkipWindowsUpdates"]
    else:
        SkipWindowsUpdates = True        

    logger.info(
        "Checking for existing Image Builder WorkSpace for user, %s.", ImageBuilderUser
    )
    response = WorkspacesClient.describe_workspaces(
        DirectoryId=ImageBuilderDirectory, UserName=ImageBuilderUser, Limit=1
    )

    PreExistingBuilder = False
    for workspace in response["Workspaces"]:
        PreExistingBuilder = True

    if PreExistingBuilder:
        ImageBuilderWorkSpaceId = workspace["WorkspaceId"]
        logger.info(
            "Existing WorkSpace found, %s. Sending Start action.",
            ImageBuilderWorkSpaceId,
        )

        # Send Start WorkSpace command
        response = WorkspacesClient.start_workspaces(
            StartWorkspaceRequests=[
                {"WorkspaceId": ImageBuilderWorkSpaceId},
            ]
        )

        logger.info("Start command sent to %s.", ImageBuilderWorkSpaceId)

    else:
        logger.info("Existing WorkSpace not found, provisioning one.")
        # Create workspace
        try:
            response = WorkspacesClient.create_workspaces(
                    Workspaces=[
                            {
                                    "DirectoryId": ImageBuilderDirectory,
                                    "UserName": ImageBuilderUser,
                                    "BundleId": ImageBuilderBundleId,
                                    "UserVolumeEncryptionEnabled": False,
                                    "RootVolumeEncryptionEnabled": False,
                                    "WorkspaceProperties": {
                                            "RunningMode": "AUTO_STOP",
                                            "RunningModeAutoStopTimeoutInMinutes": 180,
                                            "RootVolumeSizeGib": ImageBuilderRootVolumeSize,
                                            "UserVolumeSizeGib": ImageBuilderUserVolumeSize,
                                            "ComputeTypeName": ImageBuilderComputeType,
                                    },
                                    "Tags": [
                                            {"Key": "Automated", "Value": "True"},
                                    ],
                            },
                    ]
            )

            logger.info(response)
            ImageBuilderWorkSpaceId = response["PendingRequests"][0]["WorkspaceId"]

            logger.info("WorkSpace creation in progress for, %s.", ImageBuilderWorkSpaceId)
        except Exception as e:
                logger.error(e)
                logger.info("Unable to deploy WorkSpace for image creation.")
                ImageBuilderWorkSpaceId = "FAILED"

    # Generate full image name using image name prefix and timestamp
    now = datetime.now()
    dt_string = now.strftime("-%Y-%m-%d-%H-%M")
    ImageName = ImageNamePrefix + dt_string
    BundleName = BundleNamePrefix + dt_string

    # Check Status of default API Gateway endpoint
    logger.info("Checking status of automation API endpoint, %s.", ImageBuilderAPI)
    api_client = boto3.client("apigateway")
    response = api_client.get_rest_api(restApiId=ImageBuilderAPI)
    EndpointDisabled = response["disableExecuteApiEndpoint"]

    # If API Gateway default endpoint is disabled, enable it.
    if EndpointDisabled:
        logger.info("API endpoint is disabled, enabling now.")
        # Enable default endpoint
        response = api_client.update_rest_api(
            restApiId=ImageBuilderAPI,
            patchOperations=[
                {
                    "op": "replace",
                    "path": "/disableExecuteApiEndpoint",
                    "value": "False",
                },
            ],
        )

        logger.info("API Endpoint enabled, deploying API update.")
        # Deploy API changes
        response = api_client.create_deployment(
            restApiId=ImageBuilderAPI,
            stageName="prod",
        )
        logger.info("API deploy complete, API will be live in approx. 30 seconds.")
    else:
        logger.info("API endpoint is already enabled, no action required.")

    return {
        "AutomationParameters": {
            "ImageBuilderUser": ImageBuilderUser,
            "ImageBuilderWorkSpaceId": ImageBuilderWorkSpaceId,
            "ImageBuilderDirectory": ImageBuilderDirectory,
            "ImageBuilderBundleId": ImageBuilderBundleId,
            "ImageBuilderProtocol": ImageBuilderProtocol,
            "ImageBuilderRootVolumeSize": ImageBuilderRootVolumeSize,
            "ImageBuilderUserVolumeSize": ImageBuilderUserVolumeSize,
            "ImageBuilderComputeType": ImageBuilderComputeType,
            "ImageBuilderSecurityGroup": ImageBuilderSecurityGroup,
            "DeleteBuilder": DeleteBuilder,
            "ImageBuilderAPI": ImageBuilderAPI,
            "DisableAPI": DisableAPI,
            "ImageNamePrefix": ImageNamePrefix,
            "ImageName": ImageName,
            "ImageDescription": ImageDescription,
            "ImageTags": ImageTags,
            "ImageNotificationARN": ImageNotificationARN,
            "ImageBuilderIdArray": {"WorkspaceId": ImageBuilderWorkSpaceId},
            "CreateBundle": CreateBundle,
            "BundleNamePrefix": BundleNamePrefix,
            "BundleName": BundleName,
            "BundleDescription": BundleDescription,
            "BundleComputeType": {"Name": BundleComputeType},
            "BundleRootVolumeSize": {"Capacity": BundleRootVolumeSize},
            "BundleUserVolumeSize": {"Capacity": BundleUserVolumeSize},
            "BundleTags": BundleTags,
            "SoftwareS3Bucket": SoftwareS3Bucket,
            "InstallRoutine": InstallRoutine,
            "SkipWindowsUpdates": SkipWindowsUpdates,
            "PreExistingBuilder": PreExistingBuilder,
        }
    }