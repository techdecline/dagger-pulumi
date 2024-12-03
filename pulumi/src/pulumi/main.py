import dagger
from typing import Annotated
from dagger import dag, function, object_type, field, Doc
import json


@object_type
class Pulumi:
    """Pulumi Functions for Azure Configurations"""

    storage_account_name: Annotated[
        str, Doc("The name of the Azure Storage Account for state storage")
    ] = field(default="")
    container_name: Annotated[
        str, Doc("The name of the Azure Storage Container for state storage")
    ] = field(default="")
    stack_name: Annotated[str, Doc("The name of the Pulumi stack")] = field(default="")
    cache_dir: Annotated[str, Doc("The directory for caching Python Dependencies within the container")] = (
        field(default="/root/.cache/uv")
    )
    pulumi_image: Annotated[str, Doc("The Pulumi Docker image to use")] = field(default="pulumi/pulumi:latest")

    async def test_stack(self, container: dagger.Container) -> bool:
        """Query all existing stacks in the Pulumi state file"""
        result = await container.with_exec(["pulumi", "stack", "ls", "--json"]).stdout()
        stacks = json.loads(result)
        return any(stack.get("name") == self.stack_name for stack in stacks)

    @function
    async def create_or_select_stack(
        self,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None,
        azure_tenant_id: str | None,
    ) -> dagger.Container:
        """Create or select a stack in the Pulumi state file"""
        ctr = self.pulumi_az_base(
            config_passphrase=config_passphrase,
            infrastructure_path=infrastructure_path,
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id,
        )
        if not await self.test_stack(ctr):
            print(f"Initializing stack: {self.stack_name}")
            return await ctr.with_exec(["pulumi", "stack", "init", self.stack_name])
        else:
            print(f"Initializing stack: {self.stack_name}")
            return await ctr.with_exec(["pulumi", "stack", "select", self.stack_name])

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
        self.container_name = container_name
        self.stack_name = stack_name

        try:
            ctr = await self.create_or_select_stack(
                config_passphrase=config_passphrase,
                infrastructure_path=infrastructure_path,
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
        self.storage_account_name = storage_account_name
        self.container_name = container_name
        self.stack_name = stack_name

        ctr = await self.create_or_select_stack(
            config_passphrase=config_passphrase,
            infrastructure_path=infrastructure_path,
            azure_cli_path=azure_cli_path,
            azure_oidc_token=azure_oidc_token,
            azure_client_id=azure_client_id,
            azure_tenant_id=azure_tenant_id,
        )
        return await ctr.terminal()

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
        self.container_name = container_name
        self.stack_name = stack_name

        try:
            ctr = await self.create_or_select_stack(
                config_passphrase=config_passphrase,
                infrastructure_path=infrastructure_path,
                azure_cli_path=azure_cli_path,
                azure_oidc_token=azure_oidc_token,
                azure_client_id=azure_client_id,
                azure_tenant_id=azure_tenant_id,
            )
            return await ctr.with_exec(
                ["/bin/sh", "-c", "pulumi preview > plan.json 2>&1"]
            ).file("/infra/plan.json")
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
        self.container_name = container_name
        self.stack_name = stack_name

        try:
            ctr = await self.create_or_select_stack(
                config_passphrase=config_passphrase,
                infrastructure_path=infrastructure_path,
                azure_cli_path=azure_cli_path,
                azure_oidc_token=azure_oidc_token,
                azure_client_id=azure_client_id,
                azure_tenant_id=azure_tenant_id,
            )
            result = await ctr.with_exec(["pulumi", "up", "-f"]).stdout()
            return result
        except Exception as e:
            raise RuntimeError(f"Error during Pulumi up: {e}")

    @function 
    def build_container(self,
        infrastructure_path: dagger.Directory,
    ) -> dagger.Container:
        """Build the Pulumi container"""
        filtered_source = infrastructure_path.without_directory("venv")
        return (
            dag.container().from_(self.pulumi_image)
            .with_directory("/infra", filtered_source)
            .with_workdir("/infra")
            .with_exec(["pip", "install", "uv"])
            .with_mounted_cache(self.cache_dir, dag.cache_volume("python-313"))
            .with_exec(["pulumi", "install"])
        )

    def pulumi_az_base(
        self,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        azure_cli_path: dagger.Directory | None,
        azure_oidc_token: str | None,
        azure_client_id: str | None,
        azure_tenant_id: str | None,
    ) -> dagger.Container:
        """Returns Pulumi container with Azure Authentication"""
        blob_address = f"azblob://{self.container_name}?storage_account={self.storage_account_name}"
        ctr = self.build_container(infrastructure_path)
        if azure_cli_path:
            ctr = (
                ctr.with_directory("/root/.azure", azure_cli_path)
                .with_env_variable("AZURE_AUTH", "az")   
            )

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

        ctr = ctr.with_secret_variable(
            "PULUMI_CONFIG_PASSPHRASE", config_passphrase
        ).with_exec(["pulumi", "login", blob_address])

        return ctr
