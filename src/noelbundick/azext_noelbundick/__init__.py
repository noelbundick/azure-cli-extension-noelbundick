import importlib

from azure.cli.core import AzCommandsLoader

from ._help import helps

# Imported modules MUST implement load_command_table and load_arguments
# Imported modules CAN optionally implement init
MODULE_NAMES = [
    "ad",
    "aks",
    "browse",
    "cloudshell",
    "functionapp",
    "self_destruct",
    "vm",
]

# Example module as a clean place to start from
# MODULE_NAMES.append('sample')

MODULES = list(
    map(
        importlib.import_module,
        map(lambda m: "{}.{}".format("azext_noelbundick", m), MODULE_NAMES),
    )
)


class NoelBundickCommandsLoader(AzCommandsLoader):
    def __init__(self, cli_ctx=None):
        super(NoelBundickCommandsLoader, self).__init__(cli_ctx=cli_ctx)
        for m in MODULES:
            try:
                m.init(self)
            except AttributeError:
                # init (most likely) doesn't exist. Ignore
                pass

    def load_command_table(self, args):
        for m in MODULES:
            m.load_command_table(self, args)
        return self.command_table

    def load_arguments(self, command):
        for m in MODULES:
            m.load_arguments(self, command)


# pylint: disable=invalid-name
COMMAND_LOADER_CLS = NoelBundickCommandsLoader
