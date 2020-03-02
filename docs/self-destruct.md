# Self-Destruct Mode

Self-destruct mode is implemented by deploying a [Logic App](../src/noelbundick/azext_noelbundick/self_destruct_template_mi.json) into the same resource group as the item you want to delete. It uses a System-Assigned Managed Identity to make Azure Resource Manager API calls:

* Time-based trigger
* Delete resource
* Delete self

Because the Logic App is looking for an Azure resourceId, this works on management-plane resources only (resource groups, storage accounts, VMs). It explicitly does not work for data-plane objects like blobs or CosmosDB documents

Access is granted on-the-fly when you run the command by creating Contributor RoleAssignments on both the target resource and the Logic App itself.

## `--self-destruct`

`--self-destruct` is a magic argument that gets registered on every `az * create` command. When used, it intercepts the output of the original command to schedule automatic deletion

## Pricing

Logic Apps have a [price per execution](https://azure.microsoft.com/en-us/pricing/details/logic-apps/) billing model, with slight variations per region. In any case, this rounds out to pennies for everyday use cases. Here's an example of heavy use:

* `500` self-destruct Logic App runs per month
* `1000` actions (`500` runs * `2` actions/run)
* `$0.025` total cost (`1000` actions * `$0.000025`/action in EastUS)

## (Legacy) Service Principal usage

Self-destruct mode [originally](../src/noelbundick/azext_noelbundick/self_destruct_template_sp.json) used a predefined Service Principal that required standing access to delete your resources - quite possibly more than you wanted to grant it access to. The new Managed Identity mode, however, does require that you hold Owner on your subscription/RG. 

If you want to use the old behavior, it's still there and is activated via the additional flag `--self-destruct-sp`

### Configuration (Service Principal)

* `az self-destruct configure` - creates a service principal with Contributor on your current subscription

* `az self-destruct configure --client-id foo --client-secret bar --tenant-id baz` - if you work across multiple Azure subscriptions, or want to constrain the permissions given to the self-destruct service principal, you can provide your own

* `az self-destruct configure --force` - if you run into issues & need to change your service principal, you can overwrite the current configuration with the `--force` flag

### Validation

Self-destruct mode errs on the side of safety in the cases where it can't determine that a `DELETE` operation will be successful. At minimum, that means the service principal needs:

* To be valid at the time of self-destruct sequence activation
* The `Microsoft.Authorization/permissions/read` permission on the target resource
* The appropriate `delete` or `*` permission on the target resource
* Cannot have `delete` or `*` in the DENY section of any role assignment on the resource

> Note: the permission names vary widely, and wildcards make this a mess. The default role assignment is `Contributor`, which works great
