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
    logger.info(
        "Beginning execution of WorkSpaces_Automation_Windows_Windows_Update function."
    )

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
            "Unable to find IP address or hostname for Image Builder WorkSpace."
        )

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
        logger.info("Unable to remotely connect to the image builder WorkSpace.")

    # Install PSWindowsUpdate module https://www.powershellgallery.com/packages/PSWindowsUpdate/
    logger.info("Loading PSWindowsUpdate PowerShell module.")
    _result = session.run_ps(
        "Set-ExecutionPolicy Bypass;Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force;Install-Module -Name PSWindowsUpdate -Force"
    )

    # Create Windows Update scheduled task, to remotely install updates elevated
    logger.info("Initiating Install-WindowsUpdate scheduled task.")
    UpdateCommand = (
        "Invoke-WUJob -ComputerName "
        + ImageBuilderHostname
        + " -Script {ipmo PSWindowsUpdate; Install-WindowsUpdate -MicrosoftUpdate -AcceptAll -AutoReboot -Verbose | Out-File C:\Windows\PSWindowsUpdate.log } -RunNow -Confirm:$false -Verbose -ErrorAction Ignore"
    )
    _result = session.run_ps(UpdateCommand)

    # Return PowerShell execution policy to Windows default
    logger.info("Resetting PowerShell ExecutionPolicy.")
    _result = session.run_ps("Set-ExecutionPolicy RemoteSigned")

    logger.info(
        "Completed WorkSpaces_Automation_Windows_Windows_Updates function, returning to Step Function."
    )
    return {"Method": "Windows Updates Script", "Status": "Complete"}
