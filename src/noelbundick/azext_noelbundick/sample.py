import json
from azure.cli.core.commands import CliCommandType


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__loader__.name))

    with self.command_group('hello', custom_command_type=custom) as g:
        g.custom_command('world', 'hello_world')


def load_arguments(self, _):
    with self.argument_context('hello world') as c:
        c.argument('name', options_list=['--name', '-n'])


def hello_world(name='World'):
    return 'Hello, {}!'.format(name)
