# Noel's grab bag of Azure CLI goodies

This repo contains things that I like or find useful, offered up with absolutely zero guarantee that it will work for anyone else

![.github/workflows/build.yml](https://github.com/noelbundick/azure-cli-extension-noelbundick/workflows/.github/workflows/build.yml/badge.svg)

## How to Use

* Use `az extension add` with the [latest release](https://github.com/noelbundick/azure-cli-extension-noelbundick/releases)

## Features

### Azure Active Directory

* ~~`az ad app list-mine`: List only the applications you own~~
  * Use `az ad app list --show-mine`
* `az ad sp create-for-ralph`: Create a service principal and store the password in Key Vault ([thread](https://twitter.com/acanthamoeba/status/988185653199360002))
* `az ad sp credential list --keyvault`: List a service principal's credentials. Retreive password values from Key Vault
* ~~`az ad sp list-mine`: List only the service principals you own. Optionally filter by expiration~~
  * Use `az ad sp list --show-mine`

### Azure Cloud Shell

* `az shell ssh`: Launch Azure Cloud Shell from your terminal via [azssh](https://github.com/noelbundick/azssh)

### Azure Functions

* `az functionapp keys list`: List the host keys for an Azure Function App
* `az functionapp function keys list`: List the keys for a specific Azure Function

### Azure Kubernetes Service (AKS)

* `az aks grant-access`: Quickly allow your AKS cluster to access Azure Container Registry or other Azure resources

### Browse

* `az browse`: Interactively browse your Azure Resources via [azbrowse](https://github.com/lawrencegripper/azbrowse)

### ~~Log Analytics~~

Use `az monitor log-analytics workspace *`

* ~~`az loganalytics workspace create`~~
* ~~`az loganalytics workspace delete`~~
* ~~`az loganalytics workspace show`~~
* ~~`az loganalytics workspace update`~~
* ~~`az loganalytics workspace keys list`~~

### [Self-Destruct Mode](docs/self-destruct.md)

Set an expiration time when creating a resource or resource group, and it will automatically be deleted when the time's up.

```bash
az group create -n myRG -l eastus --self-destruct 1h
```

* `az * create --self-destruct`: Global argument that enables automatic deletion. You can specify self-destruct dates like 1d, 6h, 2h30m, 30m, etc
* `az self-destruct arm`: Enable automatic deletion on a resource that already exists
* `az self-destruct disarm`: Disable automatic deletion for a resource
* `az self-destruct list`: List items that are scheduled for deletion

#### With predefined Service Principal

The following commands enable Self-Destruct Mode with a predefined Service Principal (pre-`0.16` default behavior)

```bash
az self-destruct configure
az group create -n myRG -l eastus --self-destruct 1h
```

* `az * create --self-destruct --self-destruct-sp`: Global argument that enables automatic deletion. You can specify self-destruct dates like 1d, 6h, 2h30m, 30m, etc
* `az self-destruct arm --sp`: Enable automatic deletion on a resource that already exists
* `az self-destruct configure`: One-time configuration

### Virtual Machines

* `az vm auto-shutdown enable`
* `az vm auto-shutdown disable`
* `az vm auto-shutdown show`

## Development

```shell
# one-time configuration
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
azdev setup -r .
azdev extension add noelbundick
```
