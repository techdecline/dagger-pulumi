# Dagger-Pulumi

This repository contains various [Dagger.io](https://dagger.io) functions to automate Pulumi and Azure DevOps Operations.

## Pulumi

|Function|Description|
|---|---|
|debug-env| Launch Terminal within pre-configured Pulumi Container (including Authentication and Backend Login) |
|preview| Run Pulumi Preview and return output to STDOUT |
|preview-file| Run Pulumi Preview and return output to file |
|up| Run Pulumi Up |

## azdo

|Function|Description|
|---|---|
|comment-pr| Create new Thread within Azure DevOps Pull Request |