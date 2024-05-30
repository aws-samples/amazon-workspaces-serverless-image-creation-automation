[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit) [![cfn_nag:passing](https://img.shields.io/badge/cfn__nag-passing-brightgreen.svg)](https://github.com/stelligent/cfn_nag) ![GitHub](https://img.shields.io/github/license/aws-samples/amazon-workspaces-serverless-image-creation-automation)

# Amazon WorkSpaces Serverless Image Automation for Windows

Customers often ask how they can streamline the management and maintenance of their Amazon WorkSpaces images and bundles. The WorkSpaces service includes a rich set of [API operations](https://docs.aws.amazon.com/appstream2/latest/APIReference/Welcome.html) with which you can programmatically interact with the service.  A common customer struggle is programmatically interacting with the operating system within the WorkSpace to install and configure applications to customize their image. In this blog, I walk you through how to set up a serverless automation pipeline to create a customized WorkSpaces Windows OS based image.

This repository contains the supporting scripts for the AWS Desktop and Application Streaming blog article [Automatically create customized Amazon WorkSpaces Windows images](https://aws.amazon.com/blogs/desktop-and-application-streaming/automatically-create-customized-amazon-workspaces-windows-images/). Please refer to the blog article for guidance on deploying the solution. 

<p align="center">
   <img src="/WindowsSolutionDiagram.png" alt="Solution Diagram for Windows Image Pipeline" width=75% height=75%/>
</p>

Once you have successfully deployed the solution and ran the sample automation pipeline, you should customize the applications installed into the image and the parameters of the workflow to meet your needs.

### Customizing Executions of Step Function

For any parameters not specified in the Step Function execution JSON, a default value will be used. These default values can be viewed and/or modified on the Lambda function that creates the image builder.
1.	Navigate to the AWS Lambda console and select **Functions**.
2.	Click on the **WKS_Automation_Windows_FN01_Create_Builder_########** function.
3.	Select the **Configuration** tab.
4.	Select **Environment variables**.
5.	To change a default value, click **Edit**, modify the value, and click **Save**.


Default values were entered when the automation was deployed from CloudFormation. These values are used as inputs into the Step Function running the automation and the below parameters can be passed into the Step Function to override them. Options include:


- **ImageBuilderUser**: The user account which the image creation WorkSpace will be deployed to. This user must exist in your directory and should not have an existing WorkSpace deployed in that directory. This user account does not actually log into the WorkSpace during the process and just serves as the placeholder to allow a WorkSpace to be created. Default is set when you deploy the CloudFormation template.
- **ImageBuilderDirectory**: The directory id that the WorkSpace used to create the image will be deployed to. Default is set when you deploy the CloudFormation template. Find the directory id in the [WorkSpaces console](https://console.aws.amazon.com/workspaces/v2/directories). (d-xxxxxxxxxx)
- **ImageBuilderBundleId**: The bundle id to use as the base for building the image. Default is set when you deploy the CloudFormation template. Bundles ids are different for each Region, search the [WorkSpaces console](https://console.aws.amazon.com/workspaces/v2/bundles) for the id that matches your base image requirements (wsb-xxxxxxxxx)
- **ImageBuilderRootVolumeSize**: The size of the root volume for the image builder WorkSpace. Default is 80GB.
- **ImageBuilderUserVolumeSize**: The size of the user volume for the image builder WorkSpace. Default is 10GB.
- **ImageBuilderComputeType**: The compute type of the image builder WorkSpace. Default is set when you deploy the CloudFormation template. (See [API reference guide](https://docs.aws.amazon.com/workspaces/latest/api/API_WorkspaceProperties.html#WorkSpaces-Type-WorkspaceProperties-ComputeTypeName) for a list of valid types.)
- **ImageBuilderSecurityGroup**: The security group id attached to the image builder WorkSpace to allow the pipeline remote access.  Default SG is created by the CloudFormation template with proper permissions already in place. (sg-xxxxxxxxxxxxxxxxx)
- **DeleteBuilder**: Option to delete or keep the image builder WorkSpace after the image capture is complete. Default is True. (True | False)
- **ImageBuilderAPI**: The API id used to pass local account details to the image builder WorkSpace instance from Systems Manager parameter store. Default API is created by the CloudFormation template. Unless you manually build a new API, there should be no need to modify this parameter. (xxxxxxxxxx)
- **DisableAPI**: Option to disable the API between automation runs. If you plan on running more than one deployment in parallel, do not set this to True or the second deployment may fail due to a disabled API. Default is True. (True | False)
- **ImageNamePrefix**: The name of the image created from the automation; a timestamp is automatically appended to the end. Default is WKS_Automation.
- **ImageDescription**: The description associated with the image metadata. Default is "Image created by WorkSpaces automation pipeline. Built on the starting bundle BUNDLE_ID running BUNDLE_OS".
- **ImageTags**: The tags that you want to add to the new WorkSpace image, as an array of [tag objects](https://docs.aws.amazon.com/workspaces/latest/api/API_CreateWorkspaceImage.html#WorkSpaces-CreateWorkspaceImage-request-Tags). Default is False. [{"Key": "Key1", "Value": "Value1"},{"Key": "Key2", "Value": "Value2"}]
- **ImageNotificationARN**: ARN of the SNS topic that completion or failure emails are sent to. Default is created by the CloudFormation template. (arn:aws:sns:region:account:snstopic)
- **CreateBundle**: Option to create a bundle from the captured image. Default is False. (True | False)
- **BundleNamePrefix**: The name of the bundle created from the automation, if CreateBundle is True; a timestamp is automatically appended to the end. Default is WKS_Automation.
- **BundleDescription**:  The description associated with the bundle metadata, if CreateBundle is True. Default is "Created with automated pipeline".
- **BundleComputeType**: The compute type of the bundle, if CreateBundle is True. Default is set when you deploy the CloudFormation template. (See [API reference guide](https://docs.aws.amazon.com/workspaces/latest/api/API_WorkspaceProperties.html#WorkSpaces-Type-WorkspaceProperties-ComputeTypeName) for a list of valid types.)
- **BundleRootVolumeSize**: The size of the root volume for the bundle, if CreateBundle is True. Default is 80GB.
- **BundleUserVolumeSize**: The size of the user volume for the bundle, if CreateBundle is True. Default is 10GB.
- **BundleTags**: The tags that you want to add to the new bundle, if CreateBundle is True, as an array of [tag objects](https://docs.aws.amazon.com/workspaces/latest/api/API_CreateWorkspaceBundle.html#WorkSpaces-CreateWorkspaceBundle-request-Tags). Default is False. [{"Key": "Key1", "Value": "Value1"},{"Key": "Key2", "Value": "Value2"}]
- **SoftwareS3Bucket**: The S3 bucket name where the application silent installation packages were uploaded. If you override the default deployed by the CloudFormation template, you must update the Lambda function IAM policy (WKS_Automation_Windows_Lambda_Role__#######) to allow access to this bucket. 
- **InstallRoutine**: The installation routine to follow when creating the customized image. Default is False. If not configured, the automation will simply create a WorkSpace, run Windows Updates, and create the image. See details below on how to construct your installation routine.
- **SkipWindowsUpdates**: Option to skip the Windows Updates process as part of the image creation pipeline. Default is False. (True | False)


### Customizing installation and configuration routine

The **InstallRoutine** JSON parameter defines the steps that run on your image builder WorkSpace such as installing software, runing commands, and configuring settings. These parameter is passed as a list of lists. There are currently four types of commands supported by the pipeline:

- **DOWNLOAD_S3**: This command generates a presigned URL that allows the image builder WorkSpace to download a file from your S3 bucket. It has two additional attributes. The first is the URL to the file in S3 (s3://bucketname/file.ext), and the second is an option local path on the WorkSpace to download the file to. If the local path is not define, the file will be downloaded to a temporary folder location, C:\wks_automation, that is automatically cleaned up at the end of the pipeline. The local path must have its backslashes (\\) doubled up (\\\\) to keep the syntax valid. The Lambda function IAM policy (WKS_Automation_Windows_Lambda_Role__#######) needs to allow access to this bucket.  ["DOWNLOAD_S3","s3://wks-automation-installer-source-d3dcc6e0/putty/putty-64bit-0.80-installer.msi","c:\\wks_automation\\putty\\"]

- **DOWNLOAD_HTTP**: This command downloads a file to the image builder WorkSpace off a webpage or repository. It has two additional attributes. The first is the URL to the file, and the second is an option local path on the WorkSpace to download the file to. If the local path is not define, the file will be downloaded to a temporary folder location, C:\wks_automation, that is automatically cleaned up at the end of the pipeline. The local path must have its backslashes (\\) doubled up (\\\\) to keep the syntax valid. ["DOWNLOAD_HTTP","https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.6/npp.8.6.Installer.x64.exe"]

- **RUN_POWERSHELL**: This will run a PowerShell command on the image builder WorkSpace. Note that any use of backslashes (\\) must be doubled up (\\\\) to keep the syntax valid. ["RUN_POWERSHELL","New-ItemProperty -Path 'HKCU:\\Software\\CommunityBlog\\Scripts' -Name 'Version' -Value '42' -PropertyType DWORD -Force"]

- **RUN_COMMAND**: This will run a Command Prompt command on the image builder WorkSpace.  Note that any use of backslashes (\\) must be doubled up (\\\\) to keep the syntax valid. ["RUN_COMMAND","mkdir c:\\temp\\"]


Below is a sample InstallRoutine value that downloads two files, one from S3 and one from the internet, runs the commands to silently install both, and sets a regitry key.
```
      "InstallRoutine" : [
		["DOWNLOAD_S3","s3://wks-automation-installer-source-d3dcc6e0/putty/putty-installer.msi","c:\\wks_automation\\putty\\"],
		["RUN_COMMAND","msiexec /i c:\\wks_automation\\putty\\putty-installer.msi /qn"],
      	        ["DOWNLOAD_HTTP","https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.6/npp.8.6.Installer.x64.exe"],
		["RUN_COMMAND","c:\\wks_automation\\npp.8.6.Installer.x64.exe /S"],
                ["RUN_POWERSHELL", "New-ItemProperty -Path HKLM:\\Software\\Amazon -Name Automated_Image -Value true -PropertyType String -Force"]
```


### Windows Updates considerations
The image creation pipeline can optinally trigger Windows Updates utilizing the [PSWindowsUpdate](https://www.powershellgallery.com/packages/PSWindowsUpdate/) PowerShell module. You have the option to run the Windows Update portion of the workflow by including the **SkipWindowsUpdates** in the input JSON statement, and settings it to *false*. By default, your Windows WorkSpaces are configured to receive updates from directly from Microsoft via Windows Update over the internet. If you do not configure any Windows Updates settings with a GPO attached to your image creation OU, then your WorkSpaces will continue to receive approved updates from Microsoft.  Alternatively, you can configure your own update mechanisms for Windows. See the documentation for Windows Server Update Services (WSUS) or the systems management platform you have in place for details.


### Example JSON statement to start Step Function execution
An example JSON statement used to start an execution of the automation Step Function can be found below. In this example, several of the above parameters are entered to control the behavior of the automation. Replace the XXXXXX with the S3 bucket you uploaded the PuTTY installer into. 

```
{
    "DeleteBuilder": true,
    "CreateBundle": true,
    "SkipWindowsUpdates": true,
    "ImageNamePrefix": "WKS_Blog_Test",
    "ImageTags": [
        {
            "Key": "Automation",
            "Value": "Test run"
        },
        {
            "Key": "Blog",
            "Value": "pipeline test"
        }
    ],
    "BundleNamePrefix": "WKS_Blog_Test",
    "BundleDescription": "This bundle uses an image containing Notepad++ and PuTTY.",
    "InstallRoutine": [
        [
            "DOWNLOAD_S3",
            "s3://wks-automation-installer-source-XXXXXX/putty/putty-installer.msi",
            "c:\\wks_automation\\putty\\"
        ],
        [
            "RUN_COMMAND",
            "msiexec /i c:\\wks_automation\\putty\\putty-installer.msi /qn"
        ],
        [
            "DOWNLOAD_HTTP",
            "https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.6/npp.8.6.Installer.x64.exe"
        ],
        [
            "RUN_COMMAND",
            "c:\\wks_automation\npp.8.6.Installer.x64.exe /S"
        ],
        [
            "RUN_POWERSHELL",
            "New-ItemProperty -Path HKLM:\\Software\\Amazon -Name Automated_Image -Value true -PropertyType String -Force"
        ]
    ]
}

```

These example parameters will run the AWS Step Functions state machine resulting in a customized WorkSpaces image and bundle named WKS_Blog_Test -<timestamp>. The image will have two tags applied to it, will have PuTTY and Notepad++ installed, and should have the latest Windows Updates applied. Once complete the state machine will delete the image builder WorkSpace used to create the image.

### Troubleshooting the configuration routine
The configuration routine expects silent installs and properly formatted commands. That being said, there are times when you need to troubleshoot and investigate failures. The WKS_Automation_Windows_FN03_Configuration_Routine Lambda function writes each of the actions, and their results, to the CloudWatch log. Additionally, if  any of the commands do not return a status code of 0, then they are considered a failure and the command and return code are added to InstallRoutineErrors list. This value is passed along the Step Function steps and you can view it on the Output tabs of the Step Function. The final count of errors and their details are included in the final email that is sent at the end of the pipeline.

### Cleanup

You created several components that may generate costs based on usage. To avoid incurring future charges, remove the following resources.

1. Remove the S3 buckets used to store the .zip files containing the Lambda function code and the S3 bucket holding the software installation packages.
	- Navigate to the [Amazon S3 console](https://s3.console.aws.amazon.com/).
	- Select the bucket created in **Step 1**.
	- Select all the objects inside the bucket and choose **Delete**.
	- Confirm the deletion and choose **Delete objects**.
	- Once the bucket is empty, return to the Amazon S3 bucket page.
	- Select the bucket and choose **Delete**.
	- Confirm the deletion and choose Delete bucket.
	- Repeat these steps to remove the bucket containing the software installation packages. This bucket will be named similar to: wks-automation-installer-source-#######.

2. Remove any WorkSpaces bundles and images created from the automation.
	- Navigate to the [Amazon WorkSpaces console](https://console.aws.amazon.com/workspaces).
	- Select **Bundles**.
	- Filter the bundle list by selecting **Custom bundles** under **Filter owner**.
	- Select the bundle name to delete and choose **Delete**.
	- Choose **Delete** to confirm.
	- Select **Images**.
	- Select the image name to delete and choose **Delete**.
	- Choose **Delete** to confirm.
	- Repeat for any additional bundles and images created using the automation that are no longer needed.

3. Remove any image builder WorkSpaces created by the automation that remain.
	- Navigate to the [Amazon WorkSpaces console](https://console.aws.amazon.com/workspaces).
	- Select **WorkSpaces**.
	- To find WorkSpaces created for your image builder user, type the username into the **Filter WorkSpaces** box.
	- Select the box next to the WorkSpace to delete.
	- Select the image builder to delete, choose **Delete**.
	- Enter the *Delete* into the confirmation box, then choose **Delete**.
	- Repeat for any additional image builders left behind from the automation that are no longer needed.

 4. Remove all the remaining resources created by the CloudFormation template:
	- Navigate to the [AWS CloudFormation console](https://console.aws.amazon.com/cloudformation/).
	- Select the stack created in **Step 4**, *WorkSpaces-Windows-Image-Pipeline*.
	- Choose **Delete**. This will automatically delete the remaining resources used in the solution.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
