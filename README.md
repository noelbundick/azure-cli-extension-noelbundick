# Noel's grab bag of Azure CLI goodies

This repo contains things that I like or find useful, offered up with absolutely zero guarantee that it will work for anyone else

[![Build Status](https://dev.azure.com/noelbundick/noelbundick/_apis/build/status/azure-cli-extension-noelbundick?branchName=master)](https://dev.azure.com/noelbundick/noelbundick/_build/latest?definitionId=24?branchName=master)

## How to Use

* Use `az extension add` with the [latest release](https://github.com/noelbundick/azure-cli-extension-noelbundick/releases)
* Use the [acanthamoeba/azure-cli-extension-noelbundick](https://hub.docker.com/r/acanthamoeba/azure-cli-extension-noelbundick/) image on Docker Hub

## Features

### Azure Active Directory

* `az ad app list-mine`: List only the applications you own
* `az ad sp create-for-ralph`: Create a service principal and store the password in Key Vault ([thread](https://twitter.com/acanthamoeba/status/988185653199360002))
* `az ad sp credential list --keyvault`: List a service principal's credentials. Retreive password values from Key Vault
* `az ad sp list-mine`: List only the service principals you own. Optionally filter by expiration

### Azure Cloud Shell

* `az shell ssh`: Launch Azure Cloud Shell from your terminal via [azssh](https://github.com/noelbundick/azssh)

### Azure Functions

* `az functionapp keys list`: List the host keys for an Azure Function App
* `az functionapp function keys list`: List the keys for a specific Azure Function

### Azure Kubernetes Service (AKS)

* `az aks grant-access`: Quickly allow your AKS cluster to access Azure Container Registry or other Azure resources

### Browse

* `az browse`: Interactively browse your Azure Resources via [azbrowse](https://github.com/lawrencegripper/azbrowse)

### Log Analytics

* `az loganalytics workspace create`
* `az loganalytics workspace delete`
* `az loganalytics workspace show`
* `az loganalytics workspace update`
* `az loganalytics workspace keys list`

### [Self-Destruct Mode](docs/self-destruct.md)

Set an expiration time when creating a resource or resource group, and it will automatically be deleted when the time's up.

```bash
az self-destruct configure
az group create -n myRG -l eastus --self-destruct 1h
```

* `az * create --self-destruct`: Global argument that enables automatic deletion. You can specify self-destruct dates like 1d, 6h, 2h30m, 30m, etc
* `az self-destruct arm`: Enable automatic deletion on a resource that already exists
* `az self-destruct configure`: One-time configuration
* `az self-destruct disarm`: Disable automatic deletion for a resource
* `az self-destruct list`: List items that are scheduled for deletion

### Virtual Machines

* `az vm auto-shutdown enable`
* `az vm auto-shutdown disable`
* `az vm auto-shutdown show`

## Development

Install development tools

```bash
python3 -m venv .venv
python -m pip install 'src/noelbundick[dev]'
```

Activate the dev extension

```bash
export AZURE_EXTENSION_DIR=~/.azure/devcliextensions
pip install --upgrade --target $AZURE_EXTENSION_DIR/noelbundick src/noelbundick
```