import configparser
import os
import re
import sys
from datetime import datetime, timedelta

import requests
from azure.cli.core._environment import get_config_dir
from azure.cli.core.auth.identity import ServicePrincipalAuth, ServicePrincipalCredential
from azure.cli.core.commands import CliCommandType, LongRunningOperation
from azure.cli.core.commands.client_factory import get_mgmt_service_client
from azure.cli.core.util import get_file_json
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import Deployment, DeploymentProperties
from knack import events
from knack.arguments import CLICommandArgument
from knack.log import get_logger
from knack.util import CLIError
from msrestazure.tools import parse_resource_id

from .cli_utils import az_cli

LOGGER = get_logger(__name__)

CONFIG_DIR = get_config_dir()
SELF_DESTRUCT_PATH = os.path.join(CONFIG_DIR, "self-destruct")

# you can specify self-destruct dates like 1d, 6h, 2h30m, 30m, etc
DURATION_RE = re.compile(
    r"^((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?$"
)

# self_destruct is used to track state between different phases of the CLI
SELF_DESTRUCT = {}
SELF_DESTRUCT["active"] = False


def init(self):

    # In pre-parse args, we'll gather the --self-destruct arguments and validate them
    self.cli_ctx.register_event(
        events.EVENT_INVOKER_PRE_PARSE_ARGS, self_destruct_pre_parse_args_handler
    )

    # Inject the --self-destruct parameter to the command table
    self.cli_ctx.register_event(
        events.EVENT_INVOKER_POST_CMD_TBL_CREATE, self_destruct_add_parameters
    )

    # Strip the --self-destruct args
    self.cli_ctx.register_event(
        events.EVENT_INVOKER_POST_PARSE_ARGS, self_destruct_post_parse_args_handler
    )

    # In result transform, we can access the created resource id, and create a Logic App that will delete it at the specified time offset
    self.cli_ctx.register_event(
        events.EVENT_INVOKER_TRANSFORM_RESULT, self_destruct_transform_handler
    )


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl=f"{__name__}#{{}}")

    with self.command_group("self-destruct", custom_command_type=custom) as g:
        g.custom_command("arm", "arm")
        g.custom_command("configure", "configure_sp")
        g.custom_command("disarm", "disarm")
        g.custom_command("list", "list_self_destruct_resources")


def load_arguments(self, _):
    with self.argument_context("self-destruct arm") as c:
        c.argument("resource_id", options_list=["--id"])
        c.argument("resource_group_name", options_list=["--resource-group", "-g"])
        c.argument("timer", options_list=["--timer", "-t"])
        c.argument(
            "use_sp", options_list=["--service-principal", "--sp"], action="store_true"
        )

    with self.argument_context("self-destruct configure") as c:
        c.argument("force", options_list=["--force", "-f"])

    with self.argument_context("self-destruct disarm") as c:
        c.argument("resource_id", options_list=["--id"])
        c.argument("resource_group_name", options_list=["--resource-group", "-g"])


def list_self_destruct_resources():
    self_destruct_resources = []

    groups = az_cli(
        [
            "group",
            "list",
            "--tag",
            "self-destruct",
            "--query",
            '[].{name:name, resourceGroup: name, date:tags."self-destruct-date", type:"resourceGroup"}',
        ]
    )
    self_destruct_resources.extend(groups)

    # Bug? Can filter on tags but doesnt' return tag content
    resources = az_cli(
        [
            "resource",
            "list",
            "--tag",
            "self-destruct",
            "--query",
            '[].{name:name, resourceGroup: resourceGroup, type:type, date:tags."self-destruct-date"}',
        ]
    )
    self_destruct_resources.extend(resources)

    return self_destruct_resources


def get_resource(resource_id=None, resource_group_name=None):
    if resource_id:
        resource = az_cli(["resource", "show", "--ids", resource_id])
        resource_type = resource["type"]
        _, resource_type = resource_type.split("/")
        resource_group = resource["resourceGroup"]
        if not resource:
            raise CLIError(f"Could not find resource with id: {resource_id}")
    else:
        resource = az_cli(["group", "show", "-n", resource_group_name])
        resource_type = "resourceGroup"
        resource_group = resource_group_name
        if not resource:
            raise CLIError(
                f"Could not find resource group with name: {resource_group_name}"
            )
    return resource, resource_type, resource_group


def arm(cmd, timer, resource_id=None, resource_group_name=None, use_sp=False):
    if not any([resource_id, resource_group_name]):
        raise CLIError("You must specify a resourceId or resource group name")

    resource, _, _ = get_resource(
        resource_id=resource_id, resource_group_name=resource_group_name
    )

    if use_sp:
        read_self_destruct_sp_config()

    SELF_DESTRUCT["destroyDate"] = get_destruct_time(timer)

    deploy_self_destruct_template(cmd.cli_ctx, resource)

    if resource_id:
        args = ["resource", "update", "--ids", resource_id]
    else:
        args = ["group", "update", "-n", resource_group_name]

    args.extend(["--set", "tags.self-destruct"])
    args.extend(
        ["--set", f"tags.self-destruct-date={SELF_DESTRUCT['destroyDate']}"]
    )
    az_cli(args)


def disarm(resource_id=None, resource_group_name=None):
    if not any([resource_id, resource_group_name]):
        raise CLIError("You must specify a resourceId or resource group name")

    resource, resource_type, resource_group = get_resource(
        resource_id=resource_id, resource_group_name=resource_group_name
    )
    name = resource["name"]

    logic_name = f"self-destruct-{resource_type}-{resource_group}-{name}"

    logic_app = az_cli(
        [
            "resource",
            "show",
            "-g",
            resource_group,
            "-n",
            logic_name,
            "--resource-type",
            "Microsoft.Logic/workflows",
        ]
    )
    if not logic_app:
        raise CLIError(
            f"Could not find a self-destruct Logic App for resource with id: {name}"
        )

    az_cli(
        [
            "resource",
            "delete",
            "-g",
            resource_group,
            "-n",
            logic_name,
            "--resource-type",
            "Microsoft.Logic/workflows",
        ]
    )

    LOGGER.warning("Self-destruct sequence deactivated for %s", name)

    if resource_id:
        args = ["resource", "update", "--ids", resource_id]
    else:
        args = ["group", "update", "-n", resource_group_name]

    if "self-destruct" in resource["tags"]:
        args.extend(["--remove", "tags.self-destruct"])
    if "self-destruct-date" in resource["tags"]:
        args.extend(["--remove", "tags.self-destruct-date"])

    if len(args) > 4:
        az_cli(args)


def configure_sp(client_id=None, client_secret=None, tenant_id=None, force=False):
    config = get_config_parser()
    if force:
        try:
            os.remove(SELF_DESTRUCT_PATH)
        except Exception:  # pylint: disable=broad-except
            pass
    else:
        try:
            config.read(SELF_DESTRUCT_PATH)
            client_id = config.get("self-destruct", "client-id")
            client_secret = config.get("self-destruct", "client-secret")
            tenant_id = config.get("self-destruct", "tenant-id")
            if any([client_id, client_secret, tenant_id]):
                raise CLIError(
                    "self-destruct is already configured. Run with --force to force reconfiguration"
                )
        except CLIError:
            raise
        except Exception:  # pylint: disable=broad-except
            pass

    config.add_section("self-destruct")
    if any([client_id, client_secret, tenant_id]):
        if not all([client_id, client_secret, tenant_id]):
            raise CLIError(
                "If specifying service principal information, --client-id --client-secret and --tenant-id are all required"
            )

        config.set("self-destruct", "client-id", client_id)
        config.set("self-destruct", "client-secret", client_secret)
        config.set("self-destruct", "tenant-id", tenant_id)
    else:
        LOGGER.warning(
            "Creating a service principal with `Contributor` rights over the entire subscription"
        )
        sp = az_cli(["ad", "sp", "create-for-rbac"])
        config.set("self-destruct", "client-id", sp["appId"])
        config.set("self-destruct", "client-secret", sp["password"])
        config.set("self-destruct", "tenant-id", sp["tenant"])

    with open(SELF_DESTRUCT_PATH, "w+", encoding="utf-8") as config_file:
        config.write(config_file)

    return dict(config.items("self-destruct"))


# read self-destruct config, error if not present
def read_self_destruct_sp_config():
    try:
        config = get_config_parser()
        config.read(SELF_DESTRUCT_PATH)
        SELF_DESTRUCT["clientId"] = config.get("self-destruct", "client-id")
        SELF_DESTRUCT["clientSecret"] = config.get("self-destruct", "client-secret")
        SELF_DESTRUCT["tenantId"] = config.get("self-destruct", "tenant-id")
        if not all(SELF_DESTRUCT):
            raise CLIError(
                "Please run `az self-destruct configure` to configure self-destruct mode"
            )
    except Exception as e:
        raise CLIError(
            "Please run `az self-destruct configure` to configure self-destruct mode"
        ) from e


def get_destruct_time(delta_str):
    try:
        delta = parse_time(delta_str)
        now = datetime.utcnow()
        destroy_date = now + delta
        return destroy_date
    except Exception as e:
        raise CLIError(f"Could not parse the time offset {delta_str}") from e


# TODO: update tags of an existing resource during the Logic App ARM template deployment
def add_self_destruct_tag_args(args, destroy_date):
    exclude = {"identity", "container"}

    if exclude.intersection(args):
        LOGGER.warning(
            "Cannot add tags for this resource - it won't show in `az self-destruct list`"
        )
        return

    create_tags = True
    for idx, arg in enumerate(args):
        if arg == "--tags":
            create_tags = False
            args.insert(idx + 1, f"self-destruct-date={destroy_date}")
            args.insert(idx + 1, "self-destruct=")

    if create_tags:
        args.extend(
            ["--tags", "self-destruct", f"self-destruct-date={destroy_date}"]
        )


def self_destruct_pre_parse_args_handler(_, **kwargs):
    args = kwargs.get("args")

    # activate only when --self-destruct is activated
    if "--self-destruct" in args:

        # simple validations
        if "create" not in args:
            raise CLIError(
                "You can only initiate a self-destruct sequence when creating a resource"
            )
        if "container" in args:
            raise CLIError("`az container create` does not support tags")

        if "--self-destruct-sp" in args:
            read_self_destruct_sp_config()

        index = args.index("--self-destruct")
        delta_str = args[index + 1]
        SELF_DESTRUCT["destroyDate"] = get_destruct_time(delta_str)
        SELF_DESTRUCT["active"] = True

        add_self_destruct_tag_args(args, SELF_DESTRUCT["destroyDate"])


def self_destruct_post_parse_args_handler(_, **kwargs):
    args = kwargs.get("args")

    if "self_destruct" in args:
        delattr(args, "self_destruct")
    if "self_destruct_sp" in args:
        delattr(args, "self_destruct_sp")


def check_service_principal(
    cli_ctx, resource_id, namespace, resource_type, root_type=None
):
    try:
        # TODO: check this after updates
        # Get SP token
        cred_dict = ServicePrincipalAuth.build_credential(SELF_DESTRUCT["clientSecret"])
        sp_auth = ServicePrincipalAuth.build_from_credential(SELF_DESTRUCT["tenantId"], SELF_DESTRUCT["clientId"], cred_dict)
        cred = ServicePrincipalCredential(sp_auth)
        token = cred.acquire_token_for_client(cli_ctx.cloud.endpoints.active_directory_resource_id)

        # Check permissions for resource
        uri = f"https://management.azure.com{resource_id}/providers/Microsoft.Authorization/permissions?api-version=2015-07-01"
        headers = {"Authorization": f"Bearer {token['accessToken']}"}
        r = requests.get(uri, headers=headers)

        # TODO: Check expiration date of SP

        # If we can't read permissions - it may or may not be an actual problem
        # It's perfectly valid to create a "Delete Storage Accounts in resource group X only" cleanup role that can't read roleAssignments
        # I'd prefer always-correct behavior - so fail fast here
        if r.status_code != 200:
            error = r.json()
            LOGGER.error(
                "There was a failure when checking service principal permissions. Your self-destruct sequence cannot be activated!"
            )
            LOGGER.error("%s: %s", error["error"]["code"], error["error"]["message"])
            return False
    except Exception:  # pylint: disable=broad-except
        LOGGER.error(
            "There was a failure when checking service principal permissions. Your self-destruct sequence cannot be activated!"
        )
        return False

    # This is a mine field of complex behavior
    # action: '*' means everything, unless there's an overriding notAction
    # There can be wildcards inlined in both actions and notActions
    # Namespaces often don't match product names, etc
    permissions = r.json()["value"][0]
    reqs = {
        "*",
        f"{namespace}/*",  # Microsoft.Storage/*
        f"{namespace}/*/delete",  # Microsoft.Storage/*/delete
        f"{namespace}/{resource_type}/*",  # Microsoft.Storage/storageAccounts
        f"{namespace}/{resource_type}/delete",  # Microsoft.Storage/storageAccounts/delete
    }
    if root_type:
        reqs.add(f"{namespace}/{root_type}/{resource_type}/*")
        reqs.add(f"{namespace}/{root_type}/{resource_type}/delete")

    actions = set(permissions["actions"])
    not_actions = set(permissions["notActions"])

    if not reqs.intersection(actions) or reqs.intersection(not_actions):
        LOGGER.error(
            "Service principal delete permissions could not be verified. Your self-destruct sequence cannot be activated!"
        )
        LOGGER.error("Needed: one of %s", reqs)
        LOGGER.error("Allow: %s", actions)
        LOGGER.error("Deny: %s", not_actions)
        return False

    return True


def deploy_self_destruct_template(cli_ctx, resource):
    resource_id = resource["id"]
    parts = parse_resource_id(resource_id)

    root_type = None
    if "resource_name" in parts:
        namespace = parts["namespace"]
        resource_type = parts["resource_type"]
        if parts["type"] != parts["resource_type"]:
            root_type = parts["type"]
        resource_group = parts["resource_group"]
        # Get api-version
        api_version = az_cli(
            [
                "provider",
                "show",
                "-n",
                parts["namespace"],
                "--query",
                f"resourceTypes | [?resourceType==`{resource_type}`] | [0].apiVersions[0]",
            ],
            output_as_json=False,
        )
        name = parts["resource_name"]
    else:
        namespace = "Microsoft.Resources"
        resource_type = "resourceGroups"
        root_type = "subscriptions"
        resource_group = resource_id.split("/")[-1]
        name = resource_id.split("/")[-1]
        api_version = "2018-02-01"

    # Make sure the SP (if specified) can delete the resource
    if "client_id" in SELF_DESTRUCT:
        authorized = check_service_principal(
            cli_ctx, resource_id, namespace, resource_type, root_type=root_type
        )
        if not authorized:
            LOGGER.error(
                "You may need to run `az self-destruct configure` to reenable self-destruct mode"
            )
            return

    # Build ARM URL
    resource_uri = f"https://management.azure.com{resource_id}?api-version={api_version}"
    LOGGER.info(resource_uri)

    # Create Logic App
    if "client_id" in SELF_DESTRUCT:
        template_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "self_destruct_template_sp.json",
        )
    else:
        template_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "self_destruct_template_mi.json",
        )
    template = get_file_json(template_file)

    parameters = {}
    parameters["name"] = {
        "value": f"self-destruct-{resource_type}-{resource_group}-{name}"
    }
    parameters["utcTime"] = {
        "value": SELF_DESTRUCT["destroyDate"].strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    parameters["resourceUri"] = {"value": resource_uri}

    if "client_id" in SELF_DESTRUCT:
        parameters["servicePrincipalClientId"] = {"value": SELF_DESTRUCT["clientId"]}
        parameters["servicePrincipalClientSecret"] = {
            "value": SELF_DESTRUCT["clientSecret"]
        }
        parameters["servicePrincipalTenantId"] = {"value": SELF_DESTRUCT["tenantId"]}

    deploy_result = _deploy_arm_template_core(
        cli_ctx, resource_group, "self_destruct", template, parameters
    )
    LOGGER.warning(
        "You've activated a self-destruct sequence! %s is scheduled for deletion at %s UTC",
        resource_id,
        SELF_DESTRUCT["destroyDate"],
    )
    LOGGER.info(deploy_result)


def self_destruct_transform_handler(cli_ctx, **kwargs):
    if SELF_DESTRUCT["active"]:
        result = kwargs.get("event_data")["result"]

        # TODO: some command modules (ahem, networking...) output data in bizarro formats
        # Ex: https://github.com/Azure/azure-cli/blob/d859a0ad99e3947731c877ac9b81c4431f3422c5/src/command_modules/azure-cli-network/azure/cli/command_modules/network/_format.py#L103
        # There has to be a better way to hook in and steal the original response
        # Not sure that transforms are even guaranteed to run in order
        # This is a placeholder until I find something better
        if "newVNet" in result:
            result = result["newVNet"]
        elif "publicIp" in result:
            result = result["publicIp"]
        elif "TrafficManagerProfile" in result:
            result = result["TrafficManagerProfile"]
        elif "NewNIC" in result:
            result = result["NewNIC"]
        elif "NewNSG" in result:
            result = result["NewNSG"]

        deploy_self_destruct_template(cli_ctx, result)


# pylint: disable=unused-argument
def self_destruct_add_parameters(cli_ctx, commands_loader):
    command_table = cli_ctx.invocation.commands_loader.command_table

    if not command_table:
        return

    create_commands = [v for k, v in command_table.items() if "create" in k]
    if create_commands:
        command = create_commands[0]
        command.arguments["self_destruct"] = CLICommandArgument(
            "self_destruct",
            options_list=["--self-destruct"],
            arg_group="Self Destruct (noelbundick)",
            help="How long to wait until deletion. You can specify durations like 1d, 6h, 2h30m, 30m, etc",
        )
        command.arguments["self_destruct_sp"] = CLICommandArgument(
            "self_destruct_sp",
            options_list=["--self-destruct-sp"],
            action="store_true",
            arg_group="Self Destruct (noelbundick)",
            help="Use legacy behavior that uses a predefined Service Principal",
        )


def get_config_parser():
    if sys.version_info.major == 3:
        return configparser.ConfigParser(interpolation=None)
    return configparser.ConfigParser()


def parse_time(time_str):
    parts = DURATION_RE.match(time_str)
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)


def resource_client_factory(cli_ctx, **_):
    return get_mgmt_service_client(cli_ctx, ResourceManagementClient)


def _deploy_arm_template_core(
    cli_ctx, resource_group_name, deployment_name, template, parameters
):
    properties = DeploymentProperties(
        template=template, parameters=parameters, mode="incremental"
    )
    deployment = Deployment(properties=properties)
    client = resource_client_factory(cli_ctx)

    deploy_poll = client.deployments.create_or_update(
        resource_group_name, deployment_name, deployment, raw=False
    )
    result = LongRunningOperation(cli_ctx)(deploy_poll)
    return result
