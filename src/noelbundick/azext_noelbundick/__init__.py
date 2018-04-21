from azure.cli.core import AzCommandsLoader

from ._help import helps

class NoelBundickCommandsLoader(AzCommandsLoader):

    def __init__(self, cli_ctx=None):
        from azure.cli.core.commands import CliCommandType
        custom_type = CliCommandType(operations_tmpl='azext_noelbundick.custom#{}')
        super(NoelBundickCommandsLoader, self).__init__(cli_ctx=cli_ctx,
                                                       custom_command_type=custom_type)

    def load_command_table(self, args):
        with self.command_group('loganalytics workspace') as g:
            g.custom_command('create', 'create_workspace')
            g.custom_command('delete', 'delete_workspace')
        with self.command_group('loganalytics workspace keys') as g:
            g.custom_command('list', 'list_workspace_keys')
        return self.command_table

    def load_arguments(self, command):
        with self.argument_context('loganalytics workspace keys list') as c:
            c.argument('workspace_name', options_list=['--name', '-n'])

COMMAND_LOADER_CLS = NoelBundickCommandsLoader