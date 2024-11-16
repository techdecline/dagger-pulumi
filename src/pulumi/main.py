import dagger
from dagger import dag, function, object_type
import json


@object_type
class Pulumi:
    async def test_stack(self, container: dagger.Container, stack_name: str) -> bool:
        """Query all existing stacks in the Pulumi state file"""
        stack_output = await container.with_exec(["pulumi", "stack", "ls", "--json"]).stdout()
        stacks = json.loads(stack_output)
        return any(stack.get("name") == stack_name for stack in stacks)

    @function
    async def create_or_select_stack(
        self,
        storage_account_name: str,
        container_name: str,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        stack_name: str,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None, 
        azure_tenant_id: str | None, 
    ) -> dagger.Container:
        """Create or select a stack in the Pulumi state file"""
        ctr = self.pulumi_az_base(
            storage_account_name=storage_account_name,
            container_name=container_name,
            config_passphrase=config_passphrase,
            infrastructure_path=infrastructure_path,
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id
        )
        if not await self.test_stack(ctr, stack_name):
            return await ctr.with_exec(["pulumi", "stack", "init", stack_name])
        else:
            return await ctr.with_exec(["pulumi", "stack", "select", stack_name])

    
    
    @function
    async def preview(
        self,
        storage_account_name: str,
        container_name: str,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        stack_name: str,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None, 
        azure_tenant_id: str | None, 
    ) -> str:
        """Preview the changes to the infrastructure"""
        ctr = await self.create_or_select_stack(
            storage_account_name=storage_account_name,
            container_name=container_name,
            config_passphrase=config_passphrase,
            infrastructure_path=infrastructure_path,
            stack_name=stack_name,
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id
        )
        return await (
            # ctr.with_exec(["pip", "install", "-r", "requirements.txt"])
            ctr.with_exec(["pulumi", "preview"]).stdout()
        )
    
    @function
    async def debug_env(
        self,
        storage_account_name: str,
        container_name: str,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        stack_name: str,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None, 
        azure_tenant_id: str | None, 
    ) -> dagger.Container:
        """Preview the changes to the infrastructure"""
        ctr = await self.create_or_select_stack(
            storage_account_name=storage_account_name,
            container_name=container_name,
            config_passphrase=config_passphrase,
            infrastructure_path=infrastructure_path,
            stack_name=stack_name,
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id, 
        )
        return await (
            ctr.terminal()
        )
    
    @function
    async def up(
        self,
        storage_account_name: str,
        container_name: str,
        infrastructure_path: dagger.Directory,
        stack_name: str,
        config_passphrase: dagger.Secret,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None, 
        azure_tenant_id: str | None, 
    ) -> str:
        """Preview the changes to the infrastructure"""
        ctr = await self.create_or_select_stack(
            storage_account_name=storage_account_name,
            container_name=container_name,
            config_passphrase=config_passphrase,
            infrastructure_path=infrastructure_path,
            stack_name=stack_name,
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id, 
        )
        return await (
            # ctr.with_exec(["pip", "install", "-r", "requirements.txt"])
            ctr.with_exec(["pulumi", "up","-f"]).stdout()
        )
    
    @function
    async def comment_on_pr(
        self,
        azure_devops_pat: dagger.Secret,
        organization: str,
        project: str,
        repository_id: str,
        pr_id: int,
        comment: str
    ) -> str:
        """Comment on an Azure DevOps pull request"""
        api_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository_id}/pullRequests/{pr_id}/threads?api-version=6.0"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {azure_devops_pat}"
        }
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
        response = await ctr.with_env_variable("AZURE_DEVOPS_PAT", azure_devops_pat) \
            .with_exec([
                "curl", "-X", "POST", api_url,
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Basic {azure_devops_pat}",
                "-d", json.dumps(payload)
            ]).stdout()
        return response

    def pulumi_az_base(
        self,
        storage_account_name: str,
        container_name: str,
        
        return ctr