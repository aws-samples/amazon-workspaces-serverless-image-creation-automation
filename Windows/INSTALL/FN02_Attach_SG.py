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
import secrets

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Querying for Image Builder security group in event data.")
    if "ImageBuilderSecurityGroup" in event["AutomationParameters"]:
        ImageBuilderSecurityGroup = event["AutomationParameters"][
            "ImageBuilderSecurityGroup"
        ]
        logger.info(
            "Security group found in event data: %s.", ImageBuilderSecurityGroup
        )
    else:
        logger.info("ImageBuilderSecurityGroup not found in event data.")
        # exit("No security group found.")

    # Retrieve image builder IP address from event data
    logger.info(
        "Querying for Image Builder WorkSpace IP address and hostname in event data."
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
            "Unable to find IP address or hostname for Image Builder WorkSpace."
        )

    logger.info("Writing temporary local admin information to Parameter Store.")
    # Generate password for temporary local admin account on WorkSpace
    ImageBuilderPassword = secrets.token_urlsafe(14)
    SSMParameterName = "/wks_automation/" + ImageBuilderHostname
    try:
        ssm_client = boto3.client("ssm")
        response = ssm_client.put_parameter(
            Name=SSMParameterName,
            Description="Temporary local password for WorkSpaces automation pipeline.",
            Value=ImageBuilderPassword,
            Type="SecureString",
            Overwrite=True,
            Tier="Standard",
        )
    except Exception as e:
        logger.error(e)
        logger.info("Unable to complete password generation.")

    try:
        logger.info("Querying for WorkSpace network interface id using IP address.")
        ec2_client = boto3.client("ec2")
        ec2_resource = boto3.resource("ec2")

        response = ec2_client.describe_network_interfaces(
            Filters=[
                {
                    "Name": "addresses.private-ip-address",
                    "Values": [
                        ImageBuilderIPAddress,
                    ],
                },
            ]
        )
        ImageBuilderNetworkInterface = response["NetworkInterfaces"][0][
            "NetworkInterfaceId"
        ]
        logger.info("Network interface id found: %s.", ImageBuilderNetworkInterface)

        # Get list of security groups already attached to ENI
        logger.info("Generating list of existing security groups on WorkSpace ENI.")
        WorkspaceEni = ec2_resource.NetworkInterface(ImageBuilderNetworkInterface)
        WorkspaceEniGroups = WorkspaceEni.groups
        WorkspaceEniSgIds = [eni.get("GroupId") for eni in WorkspaceEniGroups]
        logger.info(
            "Found %s existing security groups on WorkSpace ENI: %s.",
            len(WorkspaceEniGroups),
            WorkspaceEniGroups,
        )

        # Combine list of new and existing security groups to add to ENI
        logger.info(
            "Generating updated list of security groups to add to WorkSpace ENI."
        )
        if ImageBuilderSecurityGroup not in WorkspaceEniSgIds:
            logger.info(
                "Adding %s to WorkSpace ENI attach list.", ImageBuilderSecurityGroup
            )
            WorkspaceEniSgIds.append(ImageBuilderSecurityGroup)
        else:
            logger.info(
                "%s already attached to WorkSpace ENI, will not add again.",
                ImageBuilderSecurityGroup,
            )
            return {
                "statusCode": 200,
                "body": json.dumps("Security group already attached."),
            }

        # Check that no more than 5 SGs are added to WorkSpace ENI.
        if len(WorkspaceEniSgIds) < 6:
            logger.info(
                "Attaching %s security groups to ENI: %s",
                len(WorkspaceEniSgIds),
                WorkspaceEniSgIds,
            )
            WorkspaceEni.modify_attribute(Groups=WorkspaceEniSgIds)
            logger.info("Completed attachment of security groups to WorkSpace ENI.")
        else:
            logger.error("Attempting to attach more that 5 security groups, aborting.")

    except Exception as e:
        logger.error(e)
        logger.info("Unable to find network interface for Image Builder WorkSpace.")

    return {
        "statusCode": 200,
        "body": json.dumps("Security group succesfully updated!"),
    }
