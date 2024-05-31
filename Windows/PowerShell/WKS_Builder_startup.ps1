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

Import-Module Microsoft.Powershell.LocalAccounts

$computername = $env:computername
$apiInvokeUrl = "REPLACE_WITH_API_INVOKE_URL" # Found on the Output tab of the CloudFormation deployment
$username = "wks_automation"

try {
    #Retieve password for hostname from API
    Write-Host "Obtaining local administrator credentials from API."
    $apiResponse = Invoke-restmethod -Uri $apiInvokeUrl
    Write-Host "API Response: $apiResponse"

    #Decode base64 response
    $decodedResponse = [Text.Encoding]::Utf8.GetString([Convert]::FromBase64String($apiResponse))
    $password = $decodedResponse | ConvertTo-SecureString -AsPlainText -Force

    #Check if local account already exists
    $checkUser = Get-LocalUser | where-Object Name -eq $username | Measure-Object
    if ($checkUser.Count -eq 0) {
        #User does not exist, create temporary local administrator for remote WinRM access
        Write-Host "Creating local user and adding to local administrators group."
        New-LocalUser $username -Password $password -Description "WorkSpaces automation WinRM administrator."
        Add-LocalGroupMember -Group "Administrators" -Member $username
    } else {
        #User already exists, update password to match value returned from API
        write-host("Updating password for local account used by automation.")
        Set-LocalUser $username -Password $password
    }
}
catch {
    Write-Host "Unable to create or update local administrator."
}

Start-Process -FilePath "C:\Windows\system32\UsoClient.exe" -ArgumentList "StartInteractiveScan"
Start-Process -FilePath "C:\Windows\system32\UsoClient.exe" -ArgumentList "StartScan"