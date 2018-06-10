import json
from azure.cli.core.commands import CliCommandType
from knack.util import CLIError
from knack.log import get_logger
from .cli_utils import az_cli

logger = get_logger(__name__)

def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__name__))

    with self.command_group('aks', custom_command_type=custom) as g:
        g.custom_command('grant-access', 'grant_access')


def load_arguments(self, _):
    with self.argument_context('aks grant-access') as c:
        c.argument('name', options_list=['--name', '-n'])
        c.argument('container_registry', options_list=['--registry', '-r'])


def grant_access(name, resource_group_name, container_registry=None, target_resource_group=None, target_resource_id=None, role=None):
    args = [container_registry, target_resource_group, target_resource_id]
    specified_args = len([x for x in args if x is not None])
    
    if specified_args == 0:
        raise CLIError('You must specify the resource to want to grant access to')

    if specified_args != 1:
        raise CLIError('You can only select one resource to grant access to at a time')
    
    aks = az_cli(['aks', 'show',
                '-n', name,
                '-g', resource_group_name])
    sp_id = aks['servicePrincipalProfile']['clientId']

    if container_registry:
        if not role:
            role = 'Reader'
        target = az_cli(['acr', 'show',
                '-n', container_registry])
        target_id = target['id']

    elif target_resource_group:
        if not role:
            role = 'Contributor'
        target = az_cli(['group', 'show',
                '-n', target_resource_group])
        target_id = target['id']
        
    elif target_resource_id:
        if not role:
            role = 'Contributor'
        target_id = target_resource_id

    # Check for the role assignment first
    # Adding a role assignment blows up if it already exists ¯\_(ツ)_/¯
    assignment = az_cli(['role', 'assignment', 'list',
                        '--assignee', sp_id,
                        '--scope', target_id,
                        '--role', role])
    if assignment:
        return assignment[0]

    result = az_cli(['role', 'assignment', 'create',
                    '--assignee', sp_id,
                    '--scope', target_id,
                    '--role', role])
    return result
