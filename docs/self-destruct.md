# Self-Destruct Mode

Self-destruct mode is implemented by deploying a [Logic App](../src/noelbundick/azext_noelbundick/self_destruct_template.json) into the same resource group as the item you want to delete. It uses a service principal to make Azure Resource Manager API calls:

* Time-based trigger
* Delete resource
* Delete self

Because the Logic App is looking for an Azure resourceId, this works on management-plane resources only (resource groups, storage accounts, VMs). It explicitly does not work for data-plane objects like blobs or CosmosDB documents

## Configuration

* `az self-destruct configure` - creates a service principal with Contributor on your current subscription

* `az self-destruct configure --client-id foo --client-secret bar --tenant-id baz` - if you work across multiple Azure subscriptions, or want to constrain the permissions given to the self-destruct service principal, you can provide your own

* `az self-destruct configure --force` - if you run into issues & need to change your service principal, you can overwrite the current configuration with the `--force` flag

## `--self-destruct`

`--self-destruct` is a magic argument that gets registered on every `az * create` command. When used, it intercepts the output of the original command to schedule automatic deletion

## Pricing

Logic Apps have a [price per execution](https://azure.microsoft.com/en-us/pricing/details/logic-apps/) billing model, with slight variations per region. In any case, this rounds out to pennies for everyday use cases. Here's an example of heavy use:

* `500` self-destruct Logic App runs per month
* `1000` actions (`500` runs * `2` actions/run)
* `$0.025` total cost (`1000` actions * `$0.000025`/action in EastUS)
