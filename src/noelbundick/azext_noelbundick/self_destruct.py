import json
import os
import sys

from azure.cli.core._environment import get_config_dir
from azure.cli.core.commands import CliCommandType
from knack.events import EVENT_INVOKER_PRE_PARSE_ARGS, EVENT_INVOKER_POST_PARSE_ARGS, EVENT_INVOKER_TRANSFORM_RESULT
from knack.log import get_logger
from knack.util import CLIError
from six.moves import configparser

logger = get_logger(__name__)

CONFIG_DIR = get_config_dir()
SELF_DESTRUCT_PATH = os.path.join(CONFIG_DIR, 'self-destruct')

self_destruct = {}
self_destruct['active'] = False

# register on pre-parse hooks
def init(self):
    self.cli_ctx.register_event(EVENT_INVOKER_PRE_PARSE_ARGS, self_destruct_pre_parse_args_handler)
    # self.cli_ctx.register_event(EVENT_INVOKER_POST_PARSE_ARGS, self_destruct_post_parse_args_handler)
    # self.cli_ctx.register_event(EVENT_INVOKER_TRANSFORM_RESULT, self_destruct_transform_handler)


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__loader__.name))

    with self.command_group('self-destruct', custom_command_type=custom) as g:
        g.custom_command('configure', 'configure')


def load_arguments(self, _):
    with self.argument_context('self-destruct configure') as c:
        c.argument('force', options_list=['--force', '-f'])


def get_config_parser():
    if sys.version_info.major == 3:
        return configparser.ConfigParser(interpolation=None)
    return configparser.ConfigParser()


def configure(force=False):
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
    config.set('self-destruct', 'client-id', 'foo')
    config.set('self-destruct', 'client-secret', 'bar')
    config.set('self-destruct', 'tenant-id', 'baz')
    
    with open(SELF_DESTRUCT_PATH, 'w+') as config_file:
        config.write(config_file)
    
    return dict(config.items('self-destruct'))


def self_destruct_pre_parse_args_handler(_, **kwargs):
    args = kwargs.get('args')

    # activate only when --self-destruct is activated
    if '--self-destruct' in args:

        # simple validations
        if 'create' not in args:
            raise CLIError('You can only initiate a self-destruct sequence when creating a resource')
        if 'container' in args:
            raise CLIError('`az container create` does not support tags')
        
        # read self-destruct config, error if not present
        try:
            config = get_config_parser()
            config.read(SELF_DESTRUCT_PATH)
            client_id = config.get('self-destruct', 'client-id')
            client_secret = config.get('self-destruct', 'client-secret')
            tenant_id = config.get('self-destruct', 'tenant-id')
        except Exception:
            raise CLIError('Please run `az self-destruct configure` to configure self-destruct mode')

        index = args.index('--self-destruct')
        timespan = args[index+1]
        destroy_date = timespan
        
        del args[index+1]
        del args[index]
        
        logger.warn('You\'ve activated self-destruct mode! This resource will be deleted at {}'.format(destroy_date))
        self_destruct['active'] = True
        
        create_tags = True
        for idx, arg in enumerate(args):
            if arg == '--tags':
                create_tags = False
                args[idx+1] = '{} self-destruct={}'.format(args[idx+1], destroy_date)

        if create_tags:
            args.extend(['--tags', 'self-destruct={}'.format(destroy_date)])


def self_destruct_post_parse_args_handler(_, **kwargs):
    if self_destruct['active']:
        logger.info('Do some destructive things!')
        #print(kwargs)
        args = vars(kwargs.get('args'))
        print(args)


def self_destruct_transform_handler(_, **kwargs):
    if self_destruct['active']:
        id = kwargs.get('event_data')['result']['id']
        print(id)