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
        azure_cli_path: dagger.Directory,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        stack_name: str,
    ) -> dagger.Container:
        """Create or select a stack in the Pulumi state file"""
        ctr = self.pulumi_az_base(
            storage_account_name,
            container_name,
            azure_cli_path,
            config_passphrase,
            infrastructure_path,
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
        azure_cli_path: dagger.Directory,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        stack_name: str,
    ) -> str:
        """Preview the changes to the infrastructure"""
        ctr = await self.create_or_select_stack(
            storage_account_name,
            container_name,
            azure_cli_path,
            config_passphrase,
            infrastructure_path,
            stack_name,
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
        azure_cli_path: dagger.Directory,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        stack_name: str,
    ) -> dagger.Container:
        """Preview the changes to the infrastructure"""
        ctr = await self.create_or_select_stack(
            storage_account_name,
            container_name,
            azure_cli_path,
            config_passphrase,
            infrastructure_path,
            stack_name,
        )
        return await (
            # ctr.with_exec(["pip", "install", "-r", "requirements.txt"])
            ctr.terminal()
        )
    
    @function
    async def up(
        self,
        storage_account_name: str,
        container_name: str,
        azure_cli_path: dagger.Directory,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
        stack_name: str,
    ) -> str:
        """Preview the changes to the infrastructure"""
        ctr = await self.create_or_select_stack(
            storage_account_name,
            container_name,
            azure_cli_path,
            config_passphrase,
            infrastructure_path,
            stack_name,
        )
        return await (
            # ctr.with_exec(["pip", "install", "-r", "requirements.txt"])
            ctr.with_exec(["pulumi", "up","-f"]).stdout()
        )

    def pulumi_az_base(
        self,
        storage_account_name: str,
        container_name: str,
        azure_cli_path: dagger.Directory,
        config_passphrase: dagger.Secret,
        infrastructure_path: dagger.Directory,
    ) -> dagger.Container:
        """Returns Pulumi container with Azure Authentication"""
        blob_address = (
            f"azblob://{container_name}?storage_account={storage_account_name}"
        )
        return (
            dag.container().from_("pulumi/pulumi:latest").with_directory("/root/.azure", azure_cli_path)
            # dag.container().from_("pulumi/pulumi-python-3.12:latest").with_directory("/root/.azure", azure_cli_path) # Azure CLI Required
            .with_env_variable("AZURE_AUTH", "az")
            .with_secret_variable("PULUMI_CONFIG_PASSPHRASE", config_passphrase)
            .with_mounted_directory("/infra", infrastructure_path)
            .without_directory("venv") # Exclude Virtual Environment from Container
            .with_workdir("/infra")
            .with_exec(["pulumi", "login", blob_address])
        )