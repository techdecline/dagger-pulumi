import json

import dagger
from azure.devops.connection import Connection
from dagger import dag, function, object_type
from msrest.authentication import BasicAuthentication


@object_type
class Azdo:
    @function
    async def comment_on_pr(
        self,
        azure_devops_pat: dagger.Secret,
        organization_url: str,
        project_name: str,
        repository_id: str,
        pr_id: str,
        comment: str,
    ) -> str:
        """Comment on an Azure DevOps pull request"""
        credentials = BasicAuthentication("", await azure_devops_pat.plaintext())
        connection = Connection(base_url=organization_url, creds=credentials)
        git_client = connection.clients.get_git_client()

        thread = git_client.create_thread(
            comment_thread={
                "comments": [{"content": comment, "commentType": 1}],
                "status": 1,
            },
            repository_id=repository_id,
            pull_request_id=int(pr_id),
            project=project_name,
        )
        return json.dumps(thread.as_dict())

    @function
    async def run_pipeline(
        self,
        azure_devops_pat: dagger.Secret,
        parameters: dict,
        organization_url: str,
        project_name: str,
        pipeline_id: int,
    ) -> str:
        """Comment on an Azure DevOps pull request"""
        credentials = BasicAuthentication("", await azure_devops_pat.plaintext())
        connection = Connection(base_url=organization_url, creds=credentials)
        build_client = connection.clients.get_build_client()

        # Queue the pipeline run
        queue_time_variables = {
            k: {"value": v} for k, v in parameters.items()
        }  # Format parameters
        build = build_client.queue_build(
            build={
                "definition": {"id": pipeline_id},
                "project": {"id": project_name},
                "parameters": queue_time_variables,
            },
            project=project_name,
        )
        return json.dumps(build.as_dict())
