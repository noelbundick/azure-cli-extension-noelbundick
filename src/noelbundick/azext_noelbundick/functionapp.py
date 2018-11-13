import json
import requests
from azure.cli.core.commands import CliCommandType
from .cli_utils import az_cli

from knack.log import get_logger
from knack.util import CLIError

logger = get_logger(__name__)


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__name__))

    with self.command_group('functionapp keys', custom_command_type=custom) as g:
        g.custom_command('list', 'list_functionapp_keys')

    with self.command_group('functionapp function keys', custom_command_type=custom) as g:
        g.custom_command('list', 'list_function_keys')


def load_arguments(self, _):
    with self.argument_context('functionapp') as c:
        c.argument('functionapp_name', options_list=['--name', '-n'])

    with self.argument_context('functionapp function keys list') as c:
        c.argument('function_name', options_list=['--function', '-f'])
        c.argument('include_all', options_list=['--all', '-a'])
    
    with self.argument_context('functionapp keys list') as c:
        c.argument('include_all', options_list=['--all', '-a'])


def list_functionapp_keys(resource_group_name, functionapp_name, include_all=False):
    function_id = az_cli(['functionapp', 'show',
                   '-g', resource_group_name,
                   '-n', functionapp_name])['id']
    url = "https://management.azure.com{}/hostruntime/admin/host/systemkeys?api-version=2018-02-01".format(function_id)
    access_token, _ = get_access_token()
    headers = {"Authorization": "Bearer {}".format(access_token)}
    keys = requests.get(url, headers=headers).json()['keys']

    if include_all:
        url = "https://management.azure.com{}/hostruntime/admin/host/systemkeys/_master?api-version=2018-02-01".format(function_id)
        master_key = requests.get(url, headers=headers).json()
        keys.append({k: master_key[k] for k in ('name', 'value')})

    return keys


def list_function_keys(resource_group_name, functionapp_name, function_name, include_all=False):
    function_id = az_cli(['functionapp', 'show',
                   '-g', resource_group_name,
                   '-n', functionapp_name])['id']
    url = "https://management.azure.com{}/hostruntime/admin/functions/{}/keys?api-version=2018-02-01".format(
        function_id, function_name)
    access_token, _ = get_access_token()
    headers = {"Authorization": "Bearer {}".format(access_token)}
    keys = requests.get(url, headers=headers).json()['keys']

    if include_all:
        host_keys = list_functionapp_keys(resource_group_name, functionapp_name, include_all=True)
        for key in host_keys:
            key.update({'type':'host'})
        keys.extend(host_keys)

    return keys


def get_access_token():
    from azure.cli.core._profile import Profile
    profile = Profile()
    creds, subscription, _ = profile.get_raw_token()
    return (creds[1], subscription)