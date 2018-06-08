import base64
import json
import requests
import uuid
from datetime import datetime, timedelta
from dateutil.parser import parse
from knack.util import CLIError
from azure.cli.core.commands import CliCommandType
from azure.cli.core.commands.parameters import get_enum_type
from .cli_utils import az_cli


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__name__))

    with self.command_group('ad app', custom_command_type=custom) as g:
        g.custom_command('list-mine', 'list_my_apps')

    with self.command_group('ad sp', custom_command_type=custom) as g:
        g.custom_command('create-for-ralph', 'create_sp_for_keyvault')
        g.custom_command('list-mine', 'list_my_sps')


def load_arguments(self, _):
    with self.argument_context('ad sp list-mine') as c:
        c.argument('expires_in', options_list=['--expires-in', '-e'])

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


def list_my_apps():
    objects = get_owned_objects()
    apps = [x for x in objects if x['objectType'] == 'Application']
    return apps


def list_my_sps(expires_in=None):
    objects = get_owned_objects()
    
    apps = dict(
        [x['appId'], x]
        for x in objects if x['objectType'] == 'Application')

    principals = [{
        'clientId': x['appId'],
        'displayName': x['displayName'],
        'objectId': x['objectId'],
        'tenantId': x['appOwnerTenantId'],
        'passwords': [
            {
                'name': base64.b64decode(p['customKeyIdentifier']).decode('UTF-16') if p['customKeyIdentifier'] else None,
                'expirationDate': p['endDate']
            } for p in apps[x['appId']]['passwordCredentials']
        ]
    } for x in objects if x['objectType'] == 'ServicePrincipal']

    if expires_in:
        delta = parse_time(expires_in)
        max_expiry = datetime.utcnow() + delta
        max_expiry = max_expiry.replace()
        
        principals = [p 
            for p in principals 
            if any(parse(pw['expirationDate']).replace(tzinfo=None) < max_expiry for pw in p['passwords'])]

    return principals


def get_owned_objects():
    token = az_cli(['account', 'get-access-token',
                    '--resource', 'https://graph.windows.net/'])
    access_token = token['accessToken']
    tenant_id = token['tenant']

    next_url = 'https://graph.windows.net/{}/me/ownedObjects?api-version=1.6'.format(tenant_id)
    headers = {
        'Authorization': 'Bearer {}'.format(access_token)
    }
    objects = []
    while True:
        result = requests.get(next_url, headers=headers).json()
        
        if 'odata.error' in result:
            raise CLIError('Request failed with {}', result['odata.error'])

        objects.extend(result['value'])
        if 'odata.nextLink' in result:
            next_url = 'https://graph.windows.net/{}/{}&api-version=1.6'.format(tenant_id, result['odata.nextLink'])
        else:
            break

    return objects


def parse_time(time_str):
    import re
    # you can specify self-destruct dates like 1d, 6h, 2h30m, 30m, etc
    duration_re = re.compile(r'^((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?$')
    parts = duration_re.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)