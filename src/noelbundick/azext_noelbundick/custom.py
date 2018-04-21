import json

from knack.log import get_logger
from knack.util import CLIError

from .cli_utils import az_cli

def list_workspace_keys(resource_group_name, workspace_name):
    keys = az_cli(['resource', 'invoke-action',
                    '-n', workspace_name,
                    '-g', resource_group_name,
                    '--resource-type', 'Microsoft.OperationalInsights/workspaces',
                    '--action', 'listKeys'])
    json_output = json.loads(keys)
    return json_output
