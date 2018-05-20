# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import json
import sys
from subprocess import STDOUT, CalledProcessError, check_output

from knack.log import get_logger
from knack.util import CLIError

logger = get_logger(__name__)

def az_cli(cmd, env=None, output_as_json=True):
  cli_cmd = prepare_cli_command(cmd, output_as_json=output_as_json)
  json_cmd_output = run_cli_command(cli_cmd, env=env)
  return json_cmd_output

# pylint: disable=inconsistent-return-statements
def run_cli_command(cmd, return_as_json=True, empty_json_as_error=False, env=None):
    try:
        cmd_output = check_output(cmd, stderr=STDOUT, universal_newlines=True, env=env)
        logger.debug('command: %s ended with output: %s', cmd, cmd_output)

        if return_as_json:
            if cmd_output:
                # SOME commands spew warnings in the output when there's not really a problem so the output can't be composed :(
                # so - we'll just take from the first { and hope for the best
                cmd_output = cmd_output[cmd_output.index("{"):] #pylint: disable=E1136

                json_output = json.loads(cmd_output)
                return json_output
            elif empty_json_as_error:
                raise CLIError("Command returned an unexpected empty string.")
            else:
                return None
        else:
            return cmd_output
    except CalledProcessError as ex:
        logger.error('command failed: %s', cmd)
        logger.error('output: %s', ex.output)
        raise ex
    except:
        logger.error('command ended with an error: %s', cmd)
        raise


def prepare_cli_command(cmd, output_as_json=True):
    full_cmd = [sys.executable, '-m', 'azure.cli'] + cmd

    if output_as_json:
        full_cmd += ['--output', 'json']
    else:
        full_cmd += ['--output', 'tsv']

    # tag newly created resources, containers don't have tags
    if 'create' in cmd and ('container' not in cmd):
        create_tags = True
        for idx, arg in enumerate(cmd):
            if arg == '--tags':
                create_tags = False
                cmd[idx+1] = cmd[idx+1] + ' created_by=noelbundick-extension'
        
        if not create_tags:
            full_cmd += ['--tags', 'created_by=noelbundick-extension']

    return full_cmd
