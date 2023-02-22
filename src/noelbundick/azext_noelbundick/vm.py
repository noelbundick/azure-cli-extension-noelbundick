import json
import re
import requests
from azure.cli.core._profile import Profile
from azure.cli.core.commands import CliCommandType
from .cli_utils import az_cli


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl=f"{__name__}#{{}}")

    with self.command_group("vm auto-shutdown", custom_command_type=custom) as g:
        g.custom_command("enable", "enable_vm_autoshutdown")
        g.custom_command("disable", "disable_vm_autoshutdown")
        g.custom_command("show", "show_vm_autoshutdown")


def load_arguments(self, _):
    with self.argument_context("vm auto-shutdown") as c:
        c.argument("vm_name", options_list=["--name", "-n"])

    with self.argument_context("vm auto-shutdown enable") as c:
        c.argument("time", options_list=["--time", "-t"])
        c.argument("timezone_id", options_list=["--timezone-id", "-tz"])


def enable_vm_autoshutdown(vm_name, resource_group_name, time, timezone_id="UTC"):
    _, subscription_id = get_access_token()
    properties = {}
    properties["status"] = "Enabled"
    properties["dailyRecurrence"] = {}
    properties["dailyRecurrence"]["time"] = time
    properties[
        "targetResourceId"
    ] = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Compute/virtualMachines/{vm_name}"
    properties["taskType"] = "ComputeVmShutdownTask"
    properties["timeZoneId"] = timezone_id

    schedule = az_cli(
        [
            "resource",
            "create",
            "-g",
            resource_group_name,
            "-n",
            f"shutdown-computevm-{vm_name}",
            "--resource-type",
            "Microsoft.DevTestLab/schedules",
            "-p",
            json.dumps(properties),
        ]
    )
    return schedule


def disable_vm_autoshutdown(vm_name, resource_group_name):
    _, subscription_id = get_access_token()
    resource_id = f"/subscriptions/{subscription_id}/resourcegroups/{resource_group_name}/providers/microsoft.devtestlab/schedules/shutdown-computevm-{vm_name}"
    return az_cli(["resource", "delete", "--ids", resource_id])


def show_vm_autoshutdown(_, vm_name, resource_group_name):
    access_token, subscription_id = get_access_token()
    schedules = get_resources(
        "Microsoft.DevTestLab",
        "schedules",
        access_token=access_token,
        subscription_id=subscription_id,
        api_version="2016-05-15",
    )

    search_string = f"^/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Compute/virtualMachines/{vm_name}$"
    regexp = re.compile(search_string)

    active_schedules = [
        x
        for x in schedules
        if x["properties"]["taskType"] == "ComputeVmShutdownTask"
        and regexp.search(x["properties"]["targetResourceId"])
    ]

    return active_schedules[0] if active_schedules else None


def get_access_token():
    profile = Profile()
    creds, subscription, _ = profile.get_raw_token()
    return (creds[1], subscription)


def get_resources(
    namespace, resource_type, access_token=None, subscription_id=None, api_version=None
):

    if api_version is None:
        api_version = get_latest_api_version(namespace, resource_type)

    if subscription_id is None:
        _, subscription_id = get_access_token()

    if access_token is None:
        access_token, _ = get_access_token()

    url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/{namespace}/{resource_type}?api-version={api_version}"
    headers = {"Authorization": f"Bearer {access_token}"}

    resources = requests.get(url, headers=headers).json()["value"]
    return resources


def get_latest_api_version(namespace, resource_type):
    query = f"resourceTypes[?resourceType=='{resource_type}'].apiVersions[0] | [0]"
    return az_cli(["provider", "show", "-n", namespace, "--query", query])
