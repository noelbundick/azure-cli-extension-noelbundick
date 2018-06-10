import json
import os
import re
import sys

from .cli_utils import az_cli
from azure.cli.core._environment import get_config_dir
from azure.cli.core.commands import CliCommandType
from azure.cli.core.util import get_file_json
from datetime import datetime, timedelta
from knack.log import get_logger
from knack.util import CLIError
from six.moves import configparser

logger = get_logger(__name__)

CONFIG_DIR = get_config_dir()
SELF_DESTRUCT_PATH = os.path.join(CONFIG_DIR, 'self-destruct')

# you can specify self-destruct dates like 1d, 6h, 2h30m, 30m, etc
duration_re = re.compile(r'^((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?$')

# self_destruct is used to track state between different phases of the CLI
self_destruct = {}
self_destruct['active'] = False

def init(self):
    from knack import events
    # In pre-parse args, we'll gather the --self-destruct arguments and validate them
    self.cli_ctx.register_event(events.EVENT_INVOKER_PRE_PARSE_ARGS, self_destruct_pre_parse_args_handler)

    # Inject the --self-destruct parameter to the command table
    self.cli_ctx.register_event(events.EVENT_INVOKER_POST_CMD_TBL_CREATE, self_destruct_add_parameters)

    # Strip the --self-destruct args
    self.cli_ctx.register_event(events.EVENT_INVOKER_POST_PARSE_ARGS, self_destruct_post_parse_args_handler)

    # In result transform, we can access the created resource id, and create a Logic App that will delete it at the specified time offset
    self.cli_ctx.register_event(events.EVENT_INVOKER_TRANSFORM_RESULT, self_destruct_transform_handler)


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__name__))

    with self.command_group('self-destruct', custom_command_type=custom) as g:
        g.custom_command('arm', 'arm')
        g.custom_command('configure', 'configure')
        g.custom_command('disarm', 'disarm')
        g.custom_command('list', 'list_self_destruct_resources')


# TODO: register --self-destruct on all 'create' commands
def load_arguments(self, _):
    with self.argument_context('self-destruct arm') as c:
        c.argument('resource_id', options_list=['--id'])
        c.argument('resource_group_name', options_list=['--resource-group', '-g'])
        c.argument('timer', options_list=['--timer', '-t'])

    with self.argument_context('self-destruct configure') as c:
        c.argument('force', options_list=['--resource-group', '-g'])
        c.argument('force', options_list=['--force', '-f'])
    
    with self.argument_context('self-destruct disarm') as c:
        c.argument('resource_id', options_list=['--id'])
        c.argument('resource_group_name', options_list=['--resource-group', '-g'])


def list_self_destruct_resources():
    self_destruct_resources = []

    groups = az_cli(['group', 'list',
                    '--tag', 'self-destruct',
                    '--query', '[].{name:name, resourceGroup: name, date:tags."self-destruct-date", type:"resourceGroup"}'])
    self_destruct_resources.extend(groups)

    # Bug? Can filter on tags but doesnt' return tag content
    resources = az_cli(['resource', 'list',
                        '--tag', 'self-destruct',
                        '--query', '[].{name:name, resourceGroup: resourceGroup, type:type, date:tags."self-destruct-date"}'])
    self_destruct_resources.extend(resources)
    
    return self_destruct_resources

def get_resource(resource_id=None, resource_group_name=None):
    if resource_id:
        resource = az_cli(['resource', 'show',
                            '--ids', resource_id])
        resource_type = resource['type']
        _, resource_type = resource_type.split('/')
        resource_group = resource['resourceGroup']
        if not resource:
            raise CLIError('Could not find resource with id: {}'.format(resource_id))
    else:
        resource = az_cli(['group', 'show',
                            '-n', resource_group_name])
        resource_type = 'resourceGroup'
        resource_group = resource_group_name
        if not resource:
            raise CLIError('Could not find resource group with name: {}'.format(resource_group_name))
    return resource, resource_type, resource_group

def arm(cmd, timer, resource_id=None, resource_group_name=None):
    if not any([resource_id, resource_group_name]):
        raise CLIError('You must specify a resourceId or resource group name')

    resource, _, _ = get_resource(resource_id=resource_id, resource_group_name=resource_group_name)
    read_self_destruct_config()
    self_destruct['destroyDate'] = get_destruct_time(timer)
    
    logger.warn('You\'ve activated a self-destruct sequence! This resource will be deleted at {} UTC'.format(self_destruct['destroyDate']))

    deploy_self_destruct_template(cmd.cli_ctx, resource)

    if resource_id:
        args = ['resource', 'update', '--ids', resource_id]
    else:
        args = ['group', 'update', '-n', resource_group_name]
    
    args.extend(['--set', 'tags.self-destruct'])
    args.extend(['--set', 'tags.self-destruct-date={}'.format(self_destruct['destroyDate'])])
    az_cli(args)


def disarm(resource_id=None, resource_group_name=None):
    if not any([resource_id, resource_group_name]):
        raise CLIError('You must specify a resourceId or resource group name')

    resource, resource_type, resource_group = get_resource(resource_id=resource_id, resource_group_name=resource_group_name)
    name = resource['name']
    
    logic_name = 'self-destruct-{}-{}-{}'.format(resource_type, resource_group, name)

    logic_app = az_cli(['resource', 'show',
                        '-g', resource_group,
                        '-n', logic_name,
                        '--resource-type', 'Microsoft.Logic/workflows'])
    if not logic_app:
        raise CLIError('Could not find a self-destruct Logic App for resource with id: {}'.format(name))

    az_cli(['resource', 'delete',
            '-g', resource_group,
            '-n', logic_name,
            '--resource-type', 'Microsoft.Logic/workflows'])
    
    logger.warn('Self-destruct sequence deactivated for {}'.format(name))

    if resource_id:
        args = ['resource', 'update', '--ids', resource_id]
    else:
        args = ['group', 'update', '-n', resource_group_name]
    
    if 'self-destruct' in resource['tags']:
        args.extend(['--remove', 'tags.self-destruct'])
    if 'self-destruct-date' in resource['tags']:
        args.extend(['--remove', 'tags.self-destruct-date'])

    if len(args) > 4:
        az_cli(args)


def configure(client_id=None, client_secret=None, tenant_id=None, force=False):
    config = get_config_parser()
    if force:
        try:
            os.remove(SELF_DESTRUCT_PATH)
        except Exception:
            pass
    else:
        try:
            config.read(SELF_DESTRUCT_PATH)
            client_id = config.get('self-destruct', 'client-id')
            client_secret = config.get('self-destruct', 'client-secret')
            tenant_id = config.get('self-destruct', 'tenant-id')
            if any([client_id, client_secret, tenant_id]):
                raise CLIError('self-destruct is already configured. Run with --force to force reconfiguration')
        except CLIError:
            raise
        except Exception:
            pass

    config.add_section('self-destruct')
    if any([client_id, client_secret, tenant_id]):
        if not all([client_id, client_secret, tenant_id]):
            raise CLIError('If specifying service principal information, --client-id --client-secret and --tenant-id are all required')
        
        config.set('self-destruct', 'client-id', client_id)
        config.set('self-destruct', 'client-secret', client_secret)
        config.set('self-destruct', 'tenant-id', tenant_id)
    else:
        logger.warn('Creating a service principal with `Contributor` rights over the entire subscription')
        sp = az_cli(['ad', 'sp', 'create-for-rbac'])
        config.set('self-destruct', 'client-id', sp['appId'])
        config.set('self-destruct', 'client-secret', sp['password'])
        config.set('self-destruct', 'tenant-id', sp['tenant'])
    
    with open(SELF_DESTRUCT_PATH, 'w+') as config_file:
        config.write(config_file)
    
    return dict(config.items('self-destruct'))


# read self-destruct config, error if not present
def read_self_destruct_config():
    try:
        config = get_config_parser()
        config.read(SELF_DESTRUCT_PATH)
        self_destruct['clientId'] = config.get('self-destruct', 'client-id')
        self_destruct['clientSecret'] = config.get('self-destruct', 'client-secret')
        self_destruct['tenantId'] = config.get('self-destruct', 'tenant-id')
        if not all(self_destruct):
            raise CLIError('Please run `az self-destruct configure` to configure self-destruct mode')
    except Exception:
        raise CLIError('Please run `az self-destruct configure` to configure self-destruct mode')


def get_destruct_time(delta_str):
    try:
        delta = parse_time(delta_str)
        now = datetime.utcnow()
        destroy_date = now + delta
        return destroy_date
    except Exception:
        raise CLIError('Could not parse the time offset {}'.format(delta_str))


def add_self_destruct_tag_args(args, destroy_date):
    create_tags = True
    for idx, arg in enumerate(args):
        if arg == '--tags':
            create_tags = False
            args.insert(idx+1, 'self-destruct-date={}'.format(destroy_date))
            args.insert(idx+1, 'self-destruct=')

    if create_tags:
        args.extend(['--tags', 'self-destruct', 'self-destruct-date={}'.format(destroy_date)])


def self_destruct_pre_parse_args_handler(_, **kwargs):
    args = kwargs.get('args')

    # activate only when --self-destruct is activated
    if '--self-destruct' in args:

        # simple validations
        if 'create' not in args:
            raise CLIError('You can only initiate a self-destruct sequence when creating a resource')
        if 'container' in args:
            raise CLIError('`az container create` does not support tags')
                
        read_self_destruct_config()

        index = args.index('--self-destruct')
        delta_str = args[index+1]
        self_destruct['destroyDate'] = get_destruct_time(delta_str)
        
        logger.warn('You\'ve activated a self-destruct sequence! This resource will be deleted at {} UTC'.format(self_destruct['destroyDate']))
        self_destruct['active'] = True

        add_self_destruct_tag_args(args, self_destruct['destroyDate'])


def self_destruct_post_parse_args_handler(_, **kwargs):
    args = kwargs.get('args')
    
    if 'self_destruct' in args:
        delattr(args, 'self_destruct')


def deploy_self_destruct_template(cli_ctx, resource):
    from msrestazure.tools import parse_resource_id
    id = resource['id']
    parts = parse_resource_id(id)
    if 'resource_name' in parts:
        resource_type = parts['resource_type']
        resource_group = parts['resource_group']
        # Get api-version
        api_version = az_cli(['provider', 'show',
                            '-n', parts['namespace'],
                            '--query', 'resourceTypes | [?resourceType==`{}`] | [0].apiVersions[0]'.format(resource_type)],
                            output_as_json=False)
        name = parts['resource_name']
    else:
        resource_type = 'resourceGroup'
        resource_group = id.split('/')[-1]
        name = id.split('/')[-1]
        api_version = '2018-02-01'
    

    # Build ARM URL
    resource_uri = "https://management.azure.com{}?api-version={}".format(id, api_version)
    logger.info(resource_uri)
    
    # Create Logic App
    template_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'self_destruct_template.json')
    template = get_file_json(template_file)
    
    parameters = {}
    parameters['name'] = {"value": 'self-destruct-{}-{}-{}'.format(resource_type, resource_group, name)}
    parameters['utcTime'] = {"value": self_destruct['destroyDate'].strftime('%Y-%m-%dT%H:%M:%SZ')}
    parameters['resourceUri'] = {"value": resource_uri}
    parameters['servicePrincipalClientId'] = {"value": self_destruct['clientId']}
    parameters['servicePrincipalClientSecret'] = {"value": self_destruct['clientSecret']}
    parameters['servicePrincipalTenantId'] = {"value": self_destruct['tenantId']}
    
    logger.warn('Creating Logic App {} to delete {} at {}'.format(parameters['name']['value'], id, self_destruct['destroyDate']))
    deploy_result = _deploy_arm_template_core(cli_ctx, resource_group, 'self_destruct', template, parameters)
    logger.info(deploy_result)


def self_destruct_transform_handler(cli_ctx, **kwargs):
    if self_destruct['active']:
        result = kwargs.get('event_data')['result']
        deploy_self_destruct_template(cli_ctx, result)

def self_destruct_add_parameters(_, **kwargs):
    from knack.arguments import CLICommandArgument
    command_table = kwargs.get('cmd_tbl')

    if not command_table:
        return

    create_commands = [v for k, v in command_table.items() if 'create' in k]
    if create_commands:
        command = create_commands[0]
        command.arguments['self_destruct'] = CLICommandArgument('self_destruct', 
                                        options_list=['--self-destruct'],
                                        arg_group='Self Destruct (noelbundick)',
                                        help='How long to wait until deletion. You can specify durations like 1d, 6h, 2h30m, 30m, etc')
        

def get_config_parser():
    if sys.version_info.major == 3:
        return configparser.ConfigParser(interpolation=None)
    return configparser.ConfigParser()


def parse_time(time_str):
    parts = duration_re.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)


def resource_client_factory(cli_ctx, **_):
    from azure.cli.core.commands.client_factory import get_mgmt_service_client
    from azure.mgmt.resource import ResourceManagementClient
    return get_mgmt_service_client(cli_ctx, ResourceManagementClient)


def _deploy_arm_template_core(cli_ctx, resource_group_name, deployment_name, template, parameters):
    from azure.mgmt.resource.resources.models import DeploymentProperties
    from azure.cli.core.commands import LongRunningOperation

    properties = DeploymentProperties(template=template, parameters=parameters, mode='incremental')
    client = resource_client_factory(cli_ctx)
    
    deploy_poll = client.deployments.create_or_update(resource_group_name, deployment_name, properties, raw=False)
    result = LongRunningOperation(cli_ctx)(deploy_poll)
    return result