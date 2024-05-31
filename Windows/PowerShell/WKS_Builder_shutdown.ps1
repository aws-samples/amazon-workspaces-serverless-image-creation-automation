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

$username = "wks_automation"

$checkUser = Get-LocalUser | where-Object Name -eq $username | Measure
if ($checkUser.Count -eq 0) {
    # User does not exist
    Write-Host "Local user does not exist."
} else {
    # User exists, remove it
    write-host("Local user account exists, cleaning up.")
    $user = Get-LocalUser -Name $username

    # Remove the user from the account database
    Remove-LocalUser -SID $user.SID

    # Remove the profile and registry of the user
    Get-CimInstance -Class Win32_UserProfile | ? SID -eq $user.SID | Remove-CimInstance
}
