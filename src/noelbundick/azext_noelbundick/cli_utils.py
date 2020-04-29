import json
import sys
from subprocess import CalledProcessError, check_output

from knack.log import get_logger
from knack.util import CLIError

LOGGER = get_logger(__name__)


def az_cli(cmd, env=None, output_as_json=True):
    cli_cmd = prepare_cli_command(cmd, output_as_json=output_as_json)
    json_cmd_output = run_cli_command(cli_cmd, output_as_json=output_as_json, env=env)
    return json_cmd_output


def run_cli_command(cmd, output_as_json=True, empty_json_as_error=False, env=None):
    try:
        cmd_output = check_output(cmd, universal_newlines=True, env=env)
        LOGGER.debug("command: %s ended with output: %s", cmd, cmd_output)

        if output_as_json:
            if cmd_output:
                json_output = json.loads(cmd_output)
                return json_output
            if empty_json_as_error:
                raise CLIError("Command returned an unexpected empty string.")
            return None

        return cmd_output.strip()
    except CalledProcessError as ex:
        LOGGER.error("command failed: %s", cmd)
        LOGGER.error("output: %s", ex.output)
        raise ex
    except Exception:
        LOGGER.error("command ended with an error: %s", cmd)
        raise


def prepare_cli_command(cmd, output_as_json=True):
    full_cmd = [sys.executable, "-m", "azure.cli"] + cmd

    if output_as_json:
        full_cmd += ["--output", "json"]
    else:
        full_cmd += ["--output", "tsv"]

    return full_cmd
