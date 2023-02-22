import os
import platform
import re
import subprocess
import tarfile
from io import BytesIO

import requests
from azure.cli.core.api import get_config_dir
from azure.cli.core.commands import CliCommandType
from azure.cli.core.commands.parameters import get_enum_type
from knack.log import get_logger

LOGGER = get_logger(__name__)


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl=f"{__name__}#{{}}")

    with self.command_group("shell", custom_command_type=custom) as g:
        g.custom_command("ssh", "launch_cloudshell")


def load_arguments(self, _):
    with self.argument_context("shell ssh") as c:
        c.argument(
            "shell",
            options_list=["--shell", "-s"],
            arg_type=get_enum_type(["bash", "pwsh"]),
        )


def get_latest_azssh(current_platform):
    target_platform = f"{current_platform.lower()}-amd64"

    r = requests.get("https://api.github.com/repos/noelbundick/azssh/releases")
    releases = r.json()

    releases = sorted(releases, key=lambda x: x["published_at"], reverse=True)
    latest = (x["browser_download_url"] for x in releases[0]["assets"])
    download = next(x for x in latest if target_platform in x)
    return download


def launch_cloudshell(shell="bash"):
    is_current = False
    config_dir = get_config_dir()
    executable = "azssh"

    current_platform = platform.system()
    if current_platform == "Windows":
        executable += ".exe"
    azssh = os.path.join(config_dir, executable)

    latest_azssh = get_latest_azssh(current_platform)

    if os.path.isfile(azssh):
        match = re.search(
            "https://github.com/noelbundick/azssh/releases/download/v(?P<version>.*)/(.*).tar.gz",
            latest_azssh,
        )
        latest_version = match.group("version")
        current_version = (
            subprocess.check_output([azssh, "version"]).decode("utf-8").strip()
        )

        LOGGER.info(
            "Current azssh: %s, Latest azssh: %s", current_version, latest_version
        )
        if latest_version == current_version:
            is_current = True

    if not is_current:
        LOGGER.warning("Downloading latest azssh from %s", latest_azssh)
        r = requests.get(latest_azssh, allow_redirects=True, stream=True)
        with tarfile.open(fileobj=BytesIO(r.content)) as tar:
            tar.extract(f"./{executable}", path=config_dir)

    LOGGER.warning("Launching Azure Cloud Shell, type `exit` to disconnect")
    os.system(f"{azssh} -s {shell}")
