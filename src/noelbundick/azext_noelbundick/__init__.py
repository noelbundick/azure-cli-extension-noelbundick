import importlib

from azure.cli.core import AzCommandsLoader

from ._help import helps

# Imported modules must implement load_command_table and load_arguments
module_names = ['ad', 'loganalytics', 'vm']

# Example module as a clean place to start from
# module_names.append('sample')

modules = list(map(importlib.import_module, map(lambda m: '{}.{}'.format('azext_noelbundick', m), module_names)))

class NoelBundickCommandsLoader(AzCommandsLoader):

    def __init__(self, cli_ctx=None):
        super(NoelBundickCommandsLoader, self).__init__(cli_ctx=cli_ctx)

    def load_command_table(self, args):
        for m in modules:
            m.load_command_table(self, args)
        return self.command_table

    def load_arguments(self, command):
        for m in modules:
            m.load_arguments(self, command)

COMMAND_LOADER_CLS = NoelBundickCommandsLoader