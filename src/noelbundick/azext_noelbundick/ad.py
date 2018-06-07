import json
from knack.util import CLIError
from azure.cli.core.commands import CliCommandType
from azure.cli.core.commands.parameters import get_enum_type
from .cli_utils import az_cli


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__name__))

    with self.command_group('ad sp', custom_command_type=custom) as g:
        g.custom_command('create-for-ralph', 'create_sp_for_keyvault')


def load_arguments(self, _):
    with self.argument_context('ad sp create-for-ralph') as c:
        c.argument('keyvault', options_list=['--keyvault', '-k'])
        c.argument('secret_name', options_list=['--secret-name', '-s'])
        c.argument('name', options_list=['--name', '-n'])
        c.argument('password', options_list=['--password', '-p'])
        c.argument('skip_assignment',
                   arg_type=get_enum_type(['false', 'true']))


def create_sp_for_keyvault(keyvault, secret_name=None, name=None, role='Contributor', scopes=None, skip_assignment=None, password=None):
    vault = az_cli(['keyvault', 'show',
                    '-n', keyvault])
    if not vault:
        raise CLIError(
            'Could not find Key Vault with name {}'.format(keyvault))

    sp_command = ['ad', 'sp', 'create-for-rbac']

    if name:
        sp_command.extend(['--name', name])
    if password:
        sp_command.extend(['--password', password])
    if role:
        sp_command.extend(['--role', role])
    if scopes:
        sp_command.extend(['--scopes', scopes])
    if skip_assignment:
        sp_command.extend(['--skip-assignment', skip_assignment])

    sp = az_cli(sp_command)

    if secret_name is None:
        secret_name = sp['displayName']

    az_cli(['keyvault', 'secret', 'set',
            '--vault-name', keyvault,
            '-n', secret_name,
            '--tags', 'sp',
            '--value', sp['password']])

    return sp
