import dagger
from typing import Annotated
from dagger import dag, function, object_type, field, Doc
import json


@object_type
class Pulumi:
    """Pulumi Functions for Azure Configurations"""
    
    storage_account_name: Annotated[str, Doc("The name of the Azure Storage Account for state storage")] = field(default="")
    container_name: Annotated[str, Doc("The name of the Azure Blob Container for state storage")] = field(default="")
    config_passphrase: Annotated[dagger.Secret, Doc("The passphrase for the Pulumi configuration")] = field(default=dagger.Secret("pulumi"))
    infrastructure_path: Annotated[dagger.Directory, Doc("The path to the Pulumi infrastructure code")] = field(default=dagger.Directory("/infra")) 
    stack_name: Annotated[str, Doc("The name of the Pulumi stack to use")] = field(default="dev")
    config_passphrase: Annotated[dagger.Secret, Doc("The passphrase for the Pulumi configuration")] = field(default=dagger.Secret(),init=False)
    ctr: dagger.Container = dag.container().from_("pulumi/pulumi:latest")
    
    async def test_stack(self) -> bool:
        """Query all existing stacks in the Pulumi state file"""
        stack_output = await self.ctr.with_exec(["pulumi", "stack", "ls", "--json"]).stdout()
        stacks = json.loads(stack_output)
        return any(stack.get("name") == self.stack_name for stack in stacks)

    @function
    async def create_or_select_stack(
        self,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None, 
        azure_tenant_id: str | None, 
    ) -> dagger.Container:
        """Create or select a stack in the Pulumi state file"""
        self.setup_azure_authentication(
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id
        )
        if not await self.test_stack(self.stack_name):
            return await self.ctr.with_exec(["pulumi", "stack", "init", self.stack_name])
        else:
            return await self.ctr.with_exec(["pulumi", "stack", "select", self.stack_name])
    
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
        
        # Setup class attributes 
        self.storage_account_name = storage_account_name
        self.container_name = container_name
        
        ctr = await self.create_or_select_stack(
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
    async def preview_file(
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
    ) -> dagger.File:
        """Preview the changes to the infrastructure"""
        
        # Setup class attributes 
        self.storage_account_name = storage_account_name
        self.container_name = container_name
        self.config_passphrase = config_passphrase
        self.infrastructure_path = infrastructure_path
        self.stack_name = stack_name
        
        ctr = await self.create_or_select_stack(
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id
        )
        
        return await (
            ctr.with_exec(["/bin/sh", "-c", "`pulumi preview > plan.json`"]) \
            .file("/infra/plan.json")            
        )
    
    @function
    async def terminal(
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
        
        # Setup class attributes 
        self.storage_account_name = storage_account_name
        self.container_name = container_name
        self.config_passphrase = config_passphrase
        self.infrastructure_path = infrastructure_path
        self.stack_name = stack_name
        
        ctr = await self.create_or_select_stack(
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id
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
        """Deploy the changes to the infrastructure"""
        
        # Setup class attributes 
        self.storage_account_name = storage_account_name
        self.container_name = container_name
        self.config_passphrase = config_passphrase
        self.infrastructure_path = infrastructure_path
        self.stack_name = stack_name
        
        ctr = await self.create_or_select_stack(
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id
        )
        
        return await (
            # ctr.with_exec(["pip", "install", "-r", "requirements.txt"])
            ctr.with_exec(["pulumi", "up","-f"]).stdout()
        )

    def setup_azure_authentication(
        self,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None, 
        azure_tenant_id: str | None, 
    ) -> None:
        """Returns Pulumi container with Azure Authentication"""
        blob_address = (
            f"azblob://{self.container_name}?storage_account={self.storage_account_name}"
        )
        filtered_source = self.infrastructure_path.without_directory("venv")
        
        if azure_cli_path:
            self.ctr.with_directory("/root/.azure", azure_cli_path)\
                .with_env_variable("AZURE_AUTH", "az")
        
        if azure_oidc_token:
            oidc_token_path = "/root/.azure/oidc_token"
            self.ctr.with_new_file(oidc_token_path, azure_oidc_token) \
                .with_env_variable("ARM_OIDC_TOKEN", azure_oidc_token) \
                .with_env_variable("AZURE_OIDC_TOKEN", azure_oidc_token) \
                .with_env_variable("ARM_USE_OIDC", "true") \
                .with_env_variable("AZURE_USE_OIDC", "true") \
                .with_env_variable("ARM_CLIENT_ID", azure_client_id) \
                .with_env_variable("AZURE_CLIENT_ID", azure_client_id) \
                .with_env_variable("ARM_TENANT_ID", azure_tenant_id) \
                .with_env_variable("AZURE_TENANT_ID", azure_tenant_id) \
                .with_env_variable("AZURE_FEDERATED_TOKEN_FILE", oidc_token_path)
        
        self.ctr \
            .with_secret_variable("PULUMI_CONFIG_PASSPHRASE", self.config_passphrase) \
            .with_directory("/infra", filtered_source) \
            .with_workdir("/infra") \
            .with_exec(["pulumi", "login", blob_address])