import requests
from azure.cli.core._profile import Profile
from azure.cli.core.commands import CliCommandType
from knack.log import get_logger

from .cli_utils import az_cli

LOGGER = get_logger(__name__)


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl=f"{__name__}#{{}}")

    with self.command_group("functionapp keys", custom_command_type=custom) as g:
        g.custom_command("list", "list_functionapp_keys")

    with self.command_group(
        "functionapp function keys", custom_command_type=custom
    ) as g:
        g.custom_command("list", "list_function_keys")


def load_arguments(self, _):
    with self.argument_context("functionapp") as c:
        c.argument("functionapp_name", options_list=["--name", "-n"])

    with self.argument_context("functionapp function keys list") as c:
        c.argument("function_name", options_list=["--function", "-f"])
        c.argument("include_all", options_list=["--all", "-a"])

    with self.argument_context("functionapp keys list") as c:
        c.argument("include_all", options_list=["--all", "-a"])


def list_functionapp_keys(resource_group_name, functionapp_name, include_all=False):
    appsettings = az_cli(
        [
            "functionapp",
            "config",
            "appsettings",
            "list",
            "-g",
            resource_group_name,
            "-n",
            functionapp_name,
        ]
    )
    version = next(
        a for a in appsettings if a["name"] == "FUNCTIONS_EXTENSION_VERSION"
    )["value"]

    # v1 and v2 return different things from ARM
    if version == "~1" or version.startswith("1"):
        return list_v1_functionapp_keys(
            resource_group_name, functionapp_name, include_all
        )

    return list_v2_functionapp_keys(resource_group_name, functionapp_name, include_all)


def list_function_keys(
    resource_group_name, functionapp_name, function_name, include_all=False
):
    appsettings = az_cli(
        [
            "functionapp",
            "config",
            "appsettings",
            "list",
            "-g",
            resource_group_name,
            "-n",
            functionapp_name,
        ]
    )
    version = next(
        a for a in appsettings if a["name"] == "FUNCTIONS_EXTENSION_VERSION"
    )["value"]

    # v1 and v2 return different things from ARM
    if version == "~1" or version.startswith("1"):
        return list_v1_function_keys(
            resource_group_name, functionapp_name, function_name, include_all
        )

    return list_v2_function_keys(
        resource_group_name, functionapp_name, function_name, include_all
    )


def list_v1_functionapp_keys(resource_group_name, functionapp_name, include_all):
    function_id = az_cli(
        ["functionapp", "show", "-g", resource_group_name, "-n", functionapp_name]
    )["id"]

    # Get a function app token, which can be exchanged for keys
    token_url = f"https://management.azure.com{function_id}/functions/admin/token?api-version=2018-02-01"
    arm_token, _ = get_access_token()
    arm_headers = {"Authorization": f"Bearer {arm_token}"}
    token_result = requests.get(token_url, headers=arm_headers)
    function_token = token_result.json()

    keys = []

    # Get the keys
    keys_url = f"https://{functionapp_name}.azurewebsites.net/admin/host/keys"
    function_headers = {"Authorization": f"Bearer {function_token}"}
    keys_result = requests.get(keys_url, headers=function_headers)
    if keys_result:
        keys.extend(keys_result.json()["keys"])

    # Get the system keys
    keys_url = f"https://{functionapp_name}.azurewebsites.net/admin/host/systemkeys"
    function_headers = {"Authorization": f"Bearer {function_token}"}
    keys_result = requests.get(keys_url, headers=function_headers)
    if keys_result:
        keys.extend(keys_result.json()["keys"])

    # The _master key isn't returned by default. Get it if --all was specified
    if include_all:
        keys_url = f"https://{functionapp_name}.azurewebsites.net/admin/host/systemkeys/_master"
        master_key = requests.get(keys_url, headers=function_headers).json()
        keys.append({k: master_key[k] for k in ("name", "value")})

    return keys


def list_v2_functionapp_keys(resource_group_name, functionapp_name, include_all):
    function_id = az_cli(
        ["functionapp", "show", "-g", resource_group_name, "-n", functionapp_name]
    )["id"]

    keys = []

    # Get the keys
    url = f"https://management.azure.com{function_id}/hostruntime/admin/host/keys?api-version=2018-02-01"
    access_token, _ = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    result = requests.get(url, headers=headers)
    if result:
        keys.extend(result.json()["keys"])

    # Get the system keys
    url = f"https://management.azure.com{function_id}/hostruntime/admin/host/systemkeys?api-version=2018-02-01"
    access_token, _ = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    result = requests.get(url, headers=headers)
    if result:
        keys.extend(result.json()["keys"])

    # The _master key isn't returned by default. Get it if --all was specified
    if include_all:
        url = f"https://management.azure.com{function_id}/hostruntime/admin/host/systemkeys/_master?api-version=2018-02-01"
        master_key = requests.get(url, headers=headers).json()
        keys.append({k: master_key[k] for k in ("name", "value")})

    return keys


def list_v1_function_keys(
    resource_group_name, functionapp_name, function_name, include_all=False
):
    function_id = az_cli(
        ["functionapp", "show", "-g", resource_group_name, "-n", functionapp_name]
    )["id"]

    # Get a function app token, which can be exchanged for keys
    token_url = f"https://management.azure.com{function_id}/functions/admin/token?api-version=2018-02-01"
    arm_token, _ = get_access_token()
    arm_headers = {"Authorization": f"Bearer {arm_token}"}
    token_result = requests.get(token_url, headers=arm_headers)
    function_token = token_result.json()

    # Get the function keys
    keys_url = f"https://{functionapp_name}.azurewebsites.net/admin/functions/{function_name}/keys"
    function_headers = {"Authorization": f"Bearer {function_token}"}
    keys = requests.get(keys_url, headers=function_headers).json()["keys"]

    # System keys can also be used but aren't returned by default. Include them if --all was specified
    if include_all:
        for key in keys:
            key.update({"type": "function"})
        host_keys = list_functionapp_keys(
            resource_group_name, functionapp_name, include_all=True
        )
        for key in host_keys:
            key.update({"type": "host"})
        keys.extend(host_keys)

    return keys


def list_v2_function_keys(
    resource_group_name, functionapp_name, function_name, include_all=False
):
    function_id = az_cli(
        ["functionapp", "show", "-g", resource_group_name, "-n", functionapp_name]
    )["id"]

    url = f"https://management.azure.com{function_id}/hostruntime/admin/functions/{function_name}/keys?api-version=2018-02-01"
    access_token, _ = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    keys = requests.get(url, headers=headers).json()["keys"]

    # System keys can also be used but aren't returned by default. Include them if --all was specified
    if include_all:
        for key in keys:
            key.update({"type": "function"})
        host_keys = list_functionapp_keys(
            resource_group_name, functionapp_name, include_all=True
        )
        for key in host_keys:
            key.update({"type": "host"})
        keys.extend(host_keys)

    return keys


def get_access_token():
    profile = Profile()
    creds, subscription, _ = profile.get_raw_token()
    return (creds[1], subscription)
