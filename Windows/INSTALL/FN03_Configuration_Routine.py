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
import time
import botocore
from os import path
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def create_presigned_url(bucket_name, object_name, expiration=600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    s3_client = boto3.client("s3")

    # Confirm file exists in S3 and function has access
    logger.info("Checking for object %s in bucket %s.", object_name, bucket_name)
    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_name)
        FileFound = True
        logger.info("Found S3 object, %s.", object_name)
    except botocore.exceptions.ClientError as error:
		# If error, add to error list
        if error.response["Error"]["Code"]:
            logger.error(
                "Unable to find S3 object, skipping generation of pre-signed URL."
            )
            FileFound = False
            ErrorMessage = [object_name, 1, "File not found in S3."]
            InstallRoutineErrors.append(ErrorMessage)
        else:
            logger.info("Found S3 object, %s.", object_name)
            FileFound = True

    # Generate a presigned URL for the S3 object
    if FileFound:
        try:
            response = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error("Unable to successfully generate pre-signed URL.")
            logging.error(e)
            ErrorMessage = [object_name, 1, "Error creating presigned URL."]
            InstallRoutineErrors.append(ErrorMessage)
            return None
    else:
        return None

    # The response contains the presigned URL
    return response


def download_http(file_url, session, dest="C:\\wks_automation\\"):
    """Downloads file to image builder WorkSpace

    :param file_url: string
    :param session: active pywinrm session
    :param dest (optional): folder to download to, slashes in path should be doubled '\\', defaults to c:\\wks_automation\\ folder
    """

    # Ensure the path ends in a trailing slash
    if dest[-1:] != "\\":
        dest = dest + "\\"

    file_name = get_filename(file_url)
    destination = dest + file_name

    # Create folder to download to
    result = session.run_ps("New-Item -Path " + dest + ' -ItemType "directory" -force')

    command = "Invoke-WebRequest -Uri " + file_url + " -OutFile " + destination
    logger.info("Downloading source file from web using command: %s", command)
    result = session.run_ps(command)
    logger.info("Return code %s.", result.status_code)

	# If status code is not 0, add to error list
    if result.status_code != 1:
        logger.error("Unable to connect to or download file, %s.", file_url)
        ErrorMessage = [file_url, 1, "Unable to connect to or download file."]
        InstallRoutineErrors.append(ErrorMessage)


def download_s3(s3_url, session, dest="C:\\wks_automation\\"):
    """Downloads file from S3 to image builder WorkSpace

    :param s3_url: string
    :param session: active pywinrm session
    :param dest (optional): folder to download to, slashes in path should be doubled '\\', defaults to c:\\wks_automation\\ folder
    """

    # Strip off s3:\\
    s3_url = s3_url.replace("s3://", "")

    # Get bucket
    S3Bucket = s3_url.split("/", 1)[0]

    # Get full path to object
    S3FullPath = s3_url.split("/", 1)[1]

    # Get just the file or object name
    S3File = s3_url.rsplit("/", 1)[-1]

    # Ensure the path ends in a trailing slash
    if dest[-1:] != "\\":
        dest = dest + "\\"

    destination = dest + S3File

    # Generate presigned URL
    S3SignedUrl = create_presigned_url(S3Bucket, S3FullPath)

    if S3SignedUrl:
        # Create folder to download to
        result = session.run_ps(
            "New-Item -Path " + dest + ' -ItemType "directory" -force'
        )

        # Download file to WorkSpace
        command = 'Invoke-WebRequest -Uri "' + S3SignedUrl + '" -OutFile ' + destination

        logger.info("Downloading source files from S3 using command: %s", command)
        result = session.run_ps(command)

        logger.info("Return code %s.", result.status_code)


def run_command(command, session):
    """Runs command on image builder WorkSpace


    :param command: string
    :param session: active pywinrm session
    :return: returns None
    """
    logger.info("Running Command: %s", command)
    result = session.run_cmd(command)
    logger.info("Return code %s.", result.status_code)

	# If status code is not 0, add to error list
    if result.status_code == 1619:
        logger.error("File not found.")
        ErrorMessage = [command, result.status_code, "File not found."]
        InstallRoutineErrors.append(ErrorMessage)
    elif result.status_code == 1:
        logger.error("Invalid command.")
        ErrorMessage = [command, result.status_code, "Invalid command."]
        InstallRoutineErrors.append(ErrorMessage)
    elif result.status_code != 0:
        logger.error("Unknown error.")
        ErrorMessage = [command, result.status_code, "Unknown error."]
        InstallRoutineErrors.append(ErrorMessage)


def run_powershell(powershell, session):
    """Runs PowerShell command on image builder WorkSpace

    :param powershell: string
    :param session: active pywinrm session
    :return: returns None
    """

    logger.info("Running PowerShell: %s", powershell)
    result = session.run_ps(powershell)
    logger.info("Return code: %s.", result.status_code)

	# If status code is not 0, add to error list
    if result.status_code != 0:
        logger.error("Error with PowerShell command.")
        ErrorMessage = [
            powershell,
            result.status_code,
            "Error with PowerShell command.",
        ]
        InstallRoutineErrors.append(ErrorMessage)

    # logger.info("Output: %s.", result.std_out)
    # logger.info("Error: %s.", result.std_err)


def get_filename(file_url):
    """Strips file name from a URL

    :param file_url: string
    :return: returns file name
    """

    fragment_removed = file_url.split("#")[0]  # keep to left of first #
    query_string_removed = fragment_removed.split("?")[0]
    scheme_removed = query_string_removed.split("://")[-1].split(":")[-1]
    if scheme_removed.find("/") == -1:
        return ""
    return path.basename(scheme_removed)


def lambda_handler(event, context):
    logger.info(
        "Beginning execution of WorkSpaces_Automation_Windows_Scripted_Install function."
    )

    global InstallRoutineErrors

    # Start timer
    StartTime = time.time()

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

    # Retrieve S3 bucket for install packages from event data
    logger.info("Querying for software package S3 bucket in event data.")
    try:
        SoftwareS3Bucket = event["AutomationParameters"]["SoftwareS3Bucket"]
        logger.info("Software S3 bucket found: %s.", SoftwareS3Bucket)
    except Exception:
        SoftwareS3Bucket = "undefined"

    # Retrieve install routine from event data
    logger.info("Querying for in-progress deployment routine in event data.")
    try:
        InstallRoutine = event["InstallRoutineRemaining"]["InstallRoutine"]
        InstallRoutineErrors = event["InstallRoutineRemaining"]["InstallRoutineErrors"]

        if InstallRoutine:
            logger.info("In-progress deployment routine found, continuing.")
    except Exception:
        logger.info("No in-progress deployment routine found.")
        InstallRoutine = False

    # If no in-progress routine found, look for new one
    if not InstallRoutine:
        logger.info("Querying for new deployment routine in event data.")
        try:
            InstallRoutine = event["AutomationParameters"]["InstallRoutine"]
            if InstallRoutine:
                logger.info("New deployment routine found, starting.")
                # Create empty list to track errors
                InstallRoutineErrors = []
            else:
                logger.info(
                    "No new or in-progress deployment routines found. Exiting function."
                )
                return {
                    "InstallRoutine": False,
                    "InstallRoutineErrors": ["No routine provided."],
                }
        except Exception:
            InstallRoutine = False
            logger.info(
                "No new or in-progress deployment routines found. Exiting function."
            )
            return {
                "InstallRoutine": False,
                "InstallRoutineErrors": ["No routine provided."],
            }

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

    # Create staging directory
    logger.info("Creating staging directory, c:\wks_automation\.")
    result = session.run_ps(
        'New-Item -Path c:\\ -Name "wks_automation" -ItemType "directory" -force'
    )
    logger.info("Return code %s.", result.status_code)

    if InstallRoutine:
        # Calculate elapsed time
        CurrentTime = time.time()
        ElapsedTime = CurrentTime - StartTime

        # Check if more than 10 minutes have passed and the routine is not empty
        while (ElapsedTime < 120) and (bool(InstallRoutine)):
            CurrentStep = InstallRoutine.pop(0)

            logger.info("Running install routine step: %s.", CurrentStep[0])

            if CurrentStep[0].casefold() == "download_s3":
                if len(CurrentStep) > 2:
                    download_s3(CurrentStep[1], session, CurrentStep[2])
                else:
                    download_s3(CurrentStep[1], session)
            elif CurrentStep[0].casefold() == "download_http":
                if len(CurrentStep) > 2:
                    download_http(CurrentStep[1], session, CurrentStep[2])
                else:
                    download_http(CurrentStep[1], session)
            elif CurrentStep[0].casefold() == "run_powershell":
                run_powershell(CurrentStep[1], session)
            elif CurrentStep[0].casefold() == "run_command":
                run_command(CurrentStep[1], session)
            else:
                logger.error("ERROR: Unknown command")

            # Calculate elapsed time
            CurrentTime = time.time()
            ElapsedTime = CurrentTime - StartTime

    if bool(InstallRoutine):
        logger.info(
            "Items still remain in deployment routine, returning to Step Function to continue."
        )
        return {
            "InstallRoutine": InstallRoutine,
            "InstallRoutineErrors": InstallRoutineErrors,
        }
    else:
        logger.info(
            "Completed deployment routine, returning to Step Function to move on."
        )
        return {"InstallRoutine": False, "InstallRoutineErrors": InstallRoutineErrors}
