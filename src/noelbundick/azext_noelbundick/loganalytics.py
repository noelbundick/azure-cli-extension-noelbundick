import json
from azure.cli.core.commands import CliCommandType
from azure.cli.core.commands.parameters import get_enum_type
from .cli_utils import az_cli


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__loader__.name))

    with self.command_group('loganalytics workspace', custom_command_type=custom) as g:
        g.custom_command('show', 'show_workspace')
        g.custom_command('create', 'create_workspace')
        g.custom_command('update', 'update_workspace')
        g.custom_command('delete', 'delete_workspace')

    with self.command_group('loganalytics workspace keys', custom_command_type=custom) as g:
        g.custom_command('list', 'list_workspace_keys')


def load_arguments(self, _):
    with self.argument_context('loganalytics workspace') as c:
        c.argument('workspace_name', options_list=['--name', '-n'])

    with self.argument_context('loganalytics workspace create') as c:
        c.argument('sku', arg_type=get_enum_type(
            ['Free', 'Standalone', 'PerNode', 'PerGB2018']))

    with self.argument_context('loganalytics workspace update') as c:
        c.argument('sku', arg_type=get_enum_type(
            ['Free', 'Standalone', 'PerNode', 'PerGB2018']))


def show_workspace(resource_group_name, workspace_name):
    workspace = az_cli(['resource', 'show',
                        '-n', workspace_name,
                        '-g', resource_group_name,
                        '--resource-type', 'Microsoft.OperationalInsights/workspaces'])
    return workspace


def create_workspace(resource_group_name, workspace_name, sku='Free', location=None):
    properties = {}
    properties['sku'] = {}
    properties['sku']['name'] = sku

    command = ['resource', 'create',
                '-n', workspace_name,
                '-g', resource_group_name,
                '--resource-type', 'Microsoft.OperationalInsights/workspaces',
                '-p', json.dumps(properties)]
    
    if location:
        command.extend(['-l', location])

    workspace = az_cli(command)
    return workspace


def update_workspace(resource_group_name, workspace_name, sku=None, retention=None):
    command = ['resource', 'update',
               '-n', workspace_name,
               '-g', resource_group_name,
               '--resource-type', 'Microsoft.OperationalInsights/workspaces']

    if sku is not None:
        if sku == 'Free':
            retention = 7
        elif sku == 'Standalone' and retention is None:
            retention = 30
        command.extend(['--set', 'properties.sku.name={}'.format(sku)])

    if retention is not None:
        command.extend(
            ['--set', 'properties.retentionInDays={}'.format(retention)])

    workspace = az_cli(command)
    return workspace


def delete_workspace(resource_group_name, workspace_name):
    az_cli(['resource', 'delete',
            '-n', workspace_name,
            '-g', resource_group_name,
            '--resource-type', 'Microsoft.OperationalInsights/workspaces'])


def list_workspace_keys(resource_group_name, workspace_name):
    keys = az_cli(['resource', 'invoke-action',
                   '-n', workspace_name,
                   '-g', resource_group_name,
                   '--resource-type', 'Microsoft.OperationalInsights/workspaces',
                   '--action', 'listKeys'])
    return keys
