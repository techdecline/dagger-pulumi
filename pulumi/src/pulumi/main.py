import dagger
from typing import Annotated
from dagger import dag, function, object_type, field, Doc
import json
import sys


@object_type
class Pulumi:
    """Pulumi Functions for Azure Configurations"""

    storage_account_name: Annotated[str, Doc("The name of the Azure Storage Account for state storage")] = field(default="")

    async def test_stack(self, container: dagger.Container, stack_name: str) -> bool:
        """Query all existing stacks in the Pulumi state file"""
        result = await container.with_exec(["pulumi", "stack", "ls", "--json"]).stdout()
        stacks = json.loads(result)
        return any(stack.get("name") == stack_name for stack in stacks)

    @function
    async def create_or_select_stack(
        self,
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
            container_name=container_name,
            config_passphrase=config_passphrase,
            infrastructure_path=infrastructure_path,
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id,
        )
        if not await self.test_stack(ctr, stack_name):
            print(f"Initializing stack: {stack_name}")
            return await ctr.with_exec(["pulumi", "stack", "init", stack_name])
        else:
            print(f"Initializing stack: {stack_name}")
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
        self.storage_account_name = storage_account_name

        try:
            ctr = await self.create_or_select_stack(
                container_name=container_name,
                config_passphrase=config_passphrase,
                infrastructure_path=infrastructure_path,
                stack_name=stack_name,
                azure_cli_path=azure_cli_path,
                azure_oidc_token=azure_oidc_token,
                azure_client_id=azure_client_id,
                azure_tenant_id=azure_tenant_id,
            )
            result = await ctr.with_exec(["pulumi", "preview"]).stdout()
            return result
        except Exception as e:
            raise RuntimeError(f"Error during Pulumi preview: {e}")

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
        """Preview the changes to the infrastructure and output to a file"""
        self.storage_account_name = storage_account_name

        try:
            ctr = await self.create_or_select_stack(
                container_name=container_name,
                config_passphrase=config_passphrase,
                infrastructure_path=infrastructure_path,
                stack_name=stack_name,
                azure_cli_path=azure_cli_path,
                azure_oidc_token=azure_oidc_token,
                azure_client_id=azure_client_id,
                azure_tenant_id=azure_tenant_id,
            )
            return await ctr.with_exec(["pulumi", "preview", "--non-interactive", "--json", "-v=9", "-e", "--logflow", "--color=always", "--logtostderr"]).file("/infra/plan.json")
        except Exception as e:
            raise RuntimeError(f"Error during Pulumi preview file generation: {e}")

    @function
    async def up(
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
        """Apply the changes to the infrastructure"""
        self.storage_account_name = storage_account_name

        try:
            ctr = await self.create_or_select_stack(
                container_name=container_name,
                config_passphrase=config_passphrase,
                infrastructure_path=infrastructure_path,
                stack_name=stack_name,
                azure_cli_path=azure_cli_path,
                azure_oidc_token=azure_oidc_token,
                azure_client_id=azure_client_id,
                azure_tenant_id=azure_tenant_id,
            )
            result = await ctr.with_exec(["pulumi", "up", "-f"]).stdout()
            return result
        except Exception as e:
            raise RuntimeError(f"Error during Pulumi up: {e}")

    def pulumi_az_base(
        self,
        container_name: str,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None,
        azure_tenant_id: str | None,
    ) -> dagger.Container:
        """Returns Pulumi container with Azure Authentication"""
        blob_address = f"azblob://{container_name}?storage_account={self.storage_account_name}"
        filtered_source = infrastructure_path.without_directory("venv")
        ctr = dag.container().from_("pulumi/pulumi:latest")

        if azure_cli_path:
            ctr = ctr.with_directory("/root/.azure", azure_cli_path).with_env_variable("AZURE_AUTH", "az")

        if azure_oidc_token:
            oidc_token_path = "/root/.azure/oidc_token"
            ctr = (
                ctr.with_new_file(oidc_token_path, azure_oidc_token)
                .with_env_variable("ARM_OIDC_TOKEN", azure_oidc_token)
                .with_env_variable("AZURE_OIDC_TOKEN", azure_oidc_token)
                .with_env_variable("ARM_USE_OIDC", "true")
                .with_env_variable("AZURE_USE_OIDC", "true")
                .with_env_variable("ARM_CLIENT_ID", azure_client_id)
                .with_env_variable("AZURE_CLIENT_ID", azure_client_id)
                .with_env_variable("ARM_TENANT_ID", azure_tenant_id)
                .with_env_variable("AZURE_TENANT_ID", azure_tenant_id)
                .with_env_variable("AZURE_FEDERATED_TOKEN_FILE", oidc_token_path)
            )

        ctr = (
            ctr.with_secret_variable("PULUMI_CONFIG_PASSPHRASE", config_passphrase)
            .with_directory("/infra", filtered_source)
            .with_workdir("/infra")
            .with_exec(["pulumi", "login", blob_address])
        )

        return ctr