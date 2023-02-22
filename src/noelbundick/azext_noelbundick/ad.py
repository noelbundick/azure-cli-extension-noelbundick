import re
from datetime import timedelta
from dateutil.parser import parse

import requests
from azure.cli.core.commands import CliCommandType
from azure.cli.core.commands.parameters import get_enum_type
from knack import events
from knack.arguments import CLICommandArgument
from knack.log import get_logger
from knack.util import CLIError

from .cli_utils import az_cli

LOGGER = get_logger(__name__)

SP_KEYVAULT = {"active": False}


def init(self):
    self.cli_ctx.register_event(
        events.EVENT_INVOKER_PRE_PARSE_ARGS, pre_parse_args_handler
    )
    self.cli_ctx.register_event(
        events.EVENT_INVOKER_POST_CMD_TBL_CREATE, add_parameters
    )
    self.cli_ctx.register_event(events.EVENT_INVOKER_POST_PARSE_ARGS, remove_parameters)
    self.cli_ctx.register_event(
        events.EVENT_INVOKER_TRANSFORM_RESULT, transform_handler
    )


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl=f"{__name__}#{{}}")

    with self.command_group("ad sp", custom_command_type=custom) as g:
        g.custom_command("create-for-ralph", "create_sp_for_keyvault")


def load_arguments(self, _):
    with self.argument_context("ad sp create-for-ralph") as c:
        c.argument("keyvault", options_list=["--keyvault", "-k"])
        c.argument("secret_name", options_list=["--secret-name", "-s"])
        c.argument("name", options_list=["--name", "-n"])
        c.argument("password", options_list=["--password", "-p"])
        c.argument("skip_assignment", arg_type=get_enum_type(["false", "true"]))


# pylint: disable=too-many-arguments
def create_sp_for_keyvault(
    keyvault,
    secret_name=None,
    name=None,
    role="Contributor",
    scopes=None,
    skip_assignment=None,
    password=None,
):
    vault = az_cli(["keyvault", "show", "-n", keyvault])
    if not vault:
        raise CLIError(f"Could not find Key Vault with name {keyvault}")

    sp_command = ["ad", "sp", "create-for-rbac"]

    if name:
        sp_command.extend(["--name", name])
    if password:
        sp_command.extend(["--password", password])
    if role:
        sp_command.extend(["--role", role])
    if scopes:
        sp_command.extend(["--scopes", scopes])
    if skip_assignment:
        sp_command.extend(["--skip-assignment", skip_assignment])

    sp = az_cli(sp_command)

    if secret_name is None:
        secret_name = sp["displayName"]

    az_cli(
        [
            "keyvault",
            "secret",
            "set",
            "--vault-name",
            keyvault,
            "-n",
            secret_name,
            "--tags",
            "sp",
            "--value",
            sp["password"],
        ]
    )

    return sp


def pre_parse_args_handler(_, **kwargs):
    args = kwargs.get("args")

    if args[:4] == ["ad", "sp", "credential", "list"] and "--keyvault" in args:
        SP_KEYVAULT["active"] = True

        index = args.index("--keyvault")
        SP_KEYVAULT["keyvault"] = args[index + 1]
        del args[index + 1]
        del args[index]

        index = args.index("--id")
        SP_KEYVAULT["id"] = args[index + 1]


# pylint: disable=unused-argument
def add_parameters(cli_ctx, commands_loader):
    command_table = cli_ctx.invocation.commands_loader.command_table

    if not command_table:
        return

    if "ad sp credential list" in command_table:
        command = command_table["ad sp credential list"]
        command.arguments["keyvault"] = CLICommandArgument(
            "keyvault",
            options_list=["--keyvault"],
            arg_group="Key Vault (noelbundick)",
            help="The name of the Key Vault to get the secret value from.",
        )


def remove_parameters(cli_ctx, **kwargs):
    command_table = cli_ctx.invocation.commands_loader.command_table

    if not command_table:
        return

    if "ad sp credential list" in command_table:
        args = kwargs.get("args")
        if "keyvault" in args:
            delattr(args, "keyvault")


def transform_handler(_, **kwargs):
    if SP_KEYVAULT["active"]:
        result = kwargs.get("event_data")["result"]

        sp = az_cli(["ad", "sp", "show", "--id", SP_KEYVAULT["id"]])
        secret = az_cli(
            [
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                SP_KEYVAULT["keyvault"],
                "-n",
                sp["displayName"],
            ]
        )
        if not secret:
            LOGGER.warning("Could not find matching secret in keyvault")
            return

        secret_date = parse(secret["attributes"]["updated"])
        matched = False
        min_date = secret_date - timedelta(seconds=30)
        max_date = secret_date + timedelta(seconds=30)
        for cred in result:
            if min_date <= parse(cred["startDate"]) <= max_date:
                cred["value"] = secret["value"]
                matched = True

        if not matched:
            LOGGER.warning(
                "Found a secret in Key Vault but couldn't match to a specific credential"
            )
            result.append(
                {
                    "customKeyIdentifier": None,
                    "endDate": None,
                    "keyId": None,
                    "source": None,
                    "startDate": None,
                    "value": secret["value"],
                }
            )


def get_owned_objects():
    token = az_cli(
        ["account", "get-access-token", "--resource", "https://graph.windows.net/"]
    )
    access_token = token["accessToken"]
    tenant_id = token["tenant"]

    next_url = f"https://graph.windows.net/{tenant_id}/me/ownedObjects?api-version=1.6"
    headers = {"Authorization": f"Bearer {access_token}"}
    objects = []
    while True:
        result = requests.get(next_url, headers=headers).json()

        if "odata.error" in result:
            raise CLIError(f"Request failed with {result['odata.error']}")

        objects.extend(result["value"])
        if "odata.nextLink" in result:
            next_url = f"https://graph.windows.net/{tenant_id}/{result['odata.nextLink']}&api-version=1.6"
        else:
            break

    return objects


def parse_time(time_str):
    # you can specify self-destruct dates like 1d, 6h, 2h30m, 30m, etc
    duration_re = re.compile(
        r"^((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?$"
    )
    parts = duration_re.match(time_str)
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)
