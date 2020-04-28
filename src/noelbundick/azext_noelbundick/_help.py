from knack.help_files import helps

helps[
    "ad sp create-for-ralph"
] = """
  type: command
  short-summary: Create a service principal and store the password in Key Vault
  parameters:
    - name: --keyvault -k
      type: string
      short-summary: The name of the Key Vault to store the secret in.
    - name: --name -n
      type: string
      short-summary: Name or app URI to associate the RBAC with. If not present, a name will be generated.
    - name: --password -p
      type: string
      short-summary: The password used to log in.
      long-summary: If not present, a random password will be generated.
    - name: --role
      type: string
      short-summary: Role of the service principal.
    - name: --scopes
      type: string
      short-summary: Space-separated list of scopes the service principal's role assignment applies to. Defaults to the root of the current subscription.
    - name: --secret-name -s
      type: string
      short-summary: The name of the Key Vault secret.
    - name: --skip-assignment
      type: string
      short-summary: Do not create default assignment.
"""

helps[
    "aks grant-access"
] = """
  type: command
  short-summary: Grant a cluster access to an Azure Container Registry or other Azure resources
  parameters:
    - name: --name -n
      type: string
      short-summary: Name of the managed cluster
    - name: --registry -r
      type: string
      short-summary: Name of an Azure Container Registry
    - name: --role
      type: string
      short-summary: Role to grant to the cluster. Defaults to 'Reader' for ACR, and 'Contributor' for everything else
    - name: --target-resource-group
      type: string
      short-summary: Name of a resource group
    - name: --target-resource-id
      type: string
      short-summary: Id of an Azure resource
"""

helps[
    "browse"
] = """
  type: command
  short-summary: Browse Azure Resources. This command is interactive.
"""

helps[
    "functionapp function"
] = """
  type: group
  short-summary: Manage specific functions az contained within function apps
"""

helps[
    "functionapp function keys"
] = """
  type: group
  short-summary: Manage function keys
"""

helps[
    "functionapp function keys list"
] = """
  type: command
  short-summary: Show the keys for an Azure Function
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the Function App that contains the function
    - name: --function -f
      type: string
      short-summary: The name of the Function
    - name: --all -a
      type: boolean
      short-summary: Specify --all if you would like to return all keys (including host keys)
"""

helps[
    "functionapp keys"
] = """
  type: group
  short-summary: Manage function app keys
"""

helps[
    "functionapp keys list"
] = """
  type: command
  short-summary: Show the keys for an Azure Function App
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the Function App
    - name: --all -a
      type: boolean
      short-summary: Specify --all if you would like to return all keys (including the _master key)
"""

helps[
    "self-destruct"
] = """
  type: group
  short-summary: Manage automatic deletion settings
"""

helps[
    "self-destruct arm"
] = """
  type: command
  short-summary: Schedule automatic deletion of a resource
  parameters:
    - name: --id
      type: string
      short-summary: The id of a resource to scheduled for deletion
    - name: --resource-group -g
      type: string
      short-summary: The name of a resource group to schedule for deletion
    - name: --timer -t
      type: string
      short-summary: How long to wait until deletion. You can specify durations like 1d, 6h, 2h30m, 30m, etc
    - name: --service-principal --sp
      type: boolean
      short-summary: Use legacy behavior that uses a predefined Service Principal
"""

helps[
    "self-destruct configure"
] = """
  type: command
  short-summary: Configure the service principal used for automatic deletion
  parameters:
    - name: --client-id
      type: string
      short-summary: The clientId of the service principal
    - name: --client-secret
      type: string
      short-summary: The password of the service principal
    - name: --force -f
      type: string
      short-summary: Overwrite saved service principal information
    - name: --tenant-id
      type: string
      short-summary: The tenantId of the service principal
"""

helps[
    "self-destruct disarm"
] = """
  type: command
  short-summary: Cancel automatic deletion of a resource
  parameters:
    - name: --id
      type: string
      short-summary: The id of a resource that is scheduled for deletion
    - name: --resource-group -g
      type: string
      short-summary: The name of a resource group that is scheduled for deletion
"""

helps[
    "self-destruct list"
] = """
  type: command
  short-summary: List items that are scheduled to be deleted based on `self-destruct` tag
"""

helps[
    "shell"
] = """
  type: group
  short-summary: Manage Azure Cloud Shell
"""

helps[
    "shell ssh"
] = """
  type: command
  short-summary: Launch Azure Cloud Shell from your terminal. This command is interactive.
  parameters:
    - name: --shell -s
      type: string
      short-summary: The shell to launch
"""

helps[
    "vm auto-shutdown"
] = """
  type: group
  short-summary: Manage auto-shutdown schedules
"""

helps[
    "vm auto-shutdown enable"
] = """
  type: command
  short-summary: Enable auto-shutdown for a VM
  long-summary: This command also overrides an existing auto-shutdown schedule
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the virtual machine
    - name: --time -t
      type: string
      short-summary: "The time, in 24hr format, to automatically shut down the VM. Ex: 1700"
    - name: --timezone-id -tz
      type: string
      short-summary: The timezone id for the specified time.
      long-summary: "Tip: specifying something bogus like '-tz foo' will spew out an error with the possible values."
"""

helps[
    "vm auto-shutdown disable"
] = """
  type: command
  short-summary: Disable auto-shutdown for a VM
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the virtual machine
"""

helps[
    "vm auto-shutdown show"
] = """
  type: command
  short-summary: Show the current auto-shutdown schedule for a VM
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the virtual machine
"""
