import dagger
import json
from dagger import dag, function, object_type
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication


@object_type
class Azdo:
    @function
    def container_echo(self, string_arg: str) -> dagger.Container:
        """Returns a container that echoes whatever string argument is provided"""
        return dag.container().from_("alpine:latest").with_exec(["echo", string_arg])

    @function
    async def comment_on_pr(
        self,
        azure_devops_pat: dagger.Secret,
        organization_url: str,
        project: str,
        repository_id: str,
        pr_id: str,
        comment: str
    ) -> str:
        """Comment on an Azure DevOps pull request"""
        credentials = BasicAuthentication('', await azure_devops_pat.plaintext())
        connection = Connection(base_url=organization_url, creds=credentials)
        git_client = connection.clients.get_git_client()

        thread = git_client.create_thread(
            comment_thread={
                "comments": [
                    {
                        "content": comment,
                        "commentType": 1
                    }
                ],
                "status": 1
            },
            repository_id=repository_id,
            pull_request_id=int(pr_id),
            project=project
        )
        return json.dumps(thread.as_dict())