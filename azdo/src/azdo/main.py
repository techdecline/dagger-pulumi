import dagger
import json
from dagger import dag, function, object_type


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
        api_url = f"{organization_url}/{project}/_apis/git/repositories/{repository_id}/pullRequests/{pr_id}/threads?api-version=6.0"
        payload = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": comment,
                    "commentType": 1
                }
            ],
            "status": 1
        }
        ctr = dag.container().from_("curlimages/curl:latest")
        response = await ctr.with_secret_variable("AZURE_DEVOPS_PAT", azure_devops_pat) \
            .with_exec([
                "curl", "-X", "POST", api_url,
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Basic {azure_devops_pat}",
                "-d", json.dumps(payload)
            ]).stdout()
        return response