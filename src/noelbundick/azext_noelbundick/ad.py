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
from knack.log import get_logger

logger = get_logger(__name__)

sp_keyvault = {'active':False}


def init(self):
    import knack.events as events
    self.cli_ctx.register_event(events.EVENT_INVOKER_PRE_PARSE_ARGS, pre_parse_args_handler)
    self.cli_ctx.register_event(events.EVENT_INVOKER_POST_CMD_TBL_CREATE, add_parameters)
    self.cli_ctx.register_event(events.EVENT_INVOKER_POST_PARSE_ARGS, remove_parameters)
    self.cli_ctx.register_event(events.EVENT_INVOKER_TRANSFORM_RESULT, transform_handler)


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


def pre_parse_args_handler(_, **kwargs):
    args = kwargs.get('args')

    if args[:4] == ['ad', 'sp', 'credential', 'list'] and '--keyvault' in args:
        sp_keyvault['active'] = True

        index = args.index('--keyvault')
        sp_keyvault['keyvault'] = args[index+1]
        del args[index+1]
        del args[index]

        index = args.index('--id')
        sp_keyvault['id'] = args[index+1]


def add_parameters(_, **kwargs):
    from knack.arguments import CLICommandArgument
    command_table = kwargs.get('cmd_tbl')

    if not command_table:
        return

    if 'ad sp credential list' in command_table:
        command = command_table['ad sp credential list']
        command.arguments['keyvault'] = CLICommandArgument('keyvault', 
                                        options_list=['--keyvault'],
                                        arg_group='Key Vault (noelbundick)',
                                        help='The name of the Key Vault to get the secret value from.')


def remove_parameters(_, **kwargs):
    args = kwargs.get('args')
    
    if 'keyvault' in args:
        delattr(args, 'keyvault')


def transform_handler(_, **kwargs):
    if sp_keyvault['active']:
        result = kwargs.get('event_data')['result']
        
        sp = az_cli(['ad', 'sp', 'show',
                    '--id', sp_keyvault['id']])
        secret = az_cli(['keyvault', 'secret', 'show',
                        '--vault-name', sp_keyvault['keyvault'],
                        '-n', sp['displayName']])
        if not secret:
            logger.warn('Could not find matching secret in keyvault')
            return

        secret_date = parse(secret['attributes']['updated'])
        matched = False
        min_date = secret_date - timedelta(seconds=30)
        max_date = secret_date + timedelta(seconds=30)
        for cred in result:
            if min_date <= parse(cred['startDate']) <= max_date:
                cred['value'] = secret['value']
                matched = True
        
        if not matched:
            logger.warn('Found a secret in Key Vault but couldn\'t match to a specific credential')
            result.append({
                'customKeyIdentifier': None,
                'endDate': None,
                'keyId': None,
                'source': None,
                'startDate': None,
                'value': secret['value']
            })


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