from knack.help_files import helps

helps['ad sp create-for-ralph'] = """
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

helps['loganalytics'] = """
  type: group
  short-summary: Manage Log Analytics
"""

helps['loganalytics workspace'] = """
  type: group
  short-summary: Manage Log Analytics workspaces
"""

helps['loganalytics workspace keys'] = """
  type: group
  short-summary: Manage Log Analytics workspace keys
"""

helps['loganalytics workspace show'] = """
  type: command
  short-summary: Show Log Analytics workspace properties
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the workspace
"""

helps['loganalytics workspace create'] = """
  type: command
  short-summary: Create a new Log Analytics workspace
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the workspace
    - name: --sku
      type: string
      short-summary: (Optional) The SKU of the workspace. The SKU must match the pricing tier for your subscription (http://aka.ms/PricingTierWarning)
"""

helps['loganalytics workspace update'] = """
  type: command
  short-summary: Update the properties of a Log Analytics workspace
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the workspace
    - name: --sku
      type: string
      short-summary: (Optional) The SKU of the workspace. The SKU must match the pricing tier for your subscription (http://aka.ms/PricingTierWarning)
    - name: --retention
      type: int
      short-summary: (Optional) The retention, in days, to keep logs. 7 days for the Free SKU. 30 to 730 days for Standalone and PerGB2018.
"""

helps['loganalytics workspace delete'] = """
  type: command
  short-summary: Delete a Log Analytics workspace
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the workspace
"""

helps['loganalytics workspace keys list'] = """
  type: command
  short-summary: Show the keys for a Log Analytics workspace
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the workspace
"""

helps['vm auto-shutdown'] = """
  type: group
  short-summary: Manage auto-shutdown schedules
"""

helps['vm auto-shutdown enable'] = """
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

helps['vm auto-shutdown disable'] = """
  type: command
  short-summary: Disable auto-shutdown for a VM
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the virtual machine
"""

helps['vm auto-shutdown show'] = """
  type: command
  short-summary: Show the current auto-shutdown schedule for a VM
  parameters:
    - name: --name -n
      type: string
      short-summary: The name of the virtual machine
"""