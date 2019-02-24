import json
import operator
import os
import re
import requests
import shutil
import subprocess
import sys
import tarfile

from azure.cli.core.api import get_config_dir
from azure.cli.core.commands import CliCommandType
from knack.log import get_logger

logger = get_logger(__name__)


def load_command_table(self, _):
    custom = CliCommandType(operations_tmpl='{}#{{}}'.format(__name__))

    with self.command_group('', custom_command_type=custom) as g:
        g.custom_command('browse', 'launch_azbrowse')


def load_arguments(self, _):
    pass


def get_latest_azbrowse():
    platform = sys.platform

    r = requests.get('https://api.github.com/repos/lawrencegripper/azbrowse/releases')
    releases = r.json()

    releases = sorted(releases, key=lambda x: x['published_at'], reverse=True)
    latest = (x['browser_download_url'] for x in releases[0]['assets'])
    download = next(x for x in latest if platform in x)
    return download


def launch_azbrowse():
    azbrowse = os.path.join(get_config_dir(), 'azbrowse')

    # azbrowse is self-updating
    if not os.path.isfile(azbrowse):
        latest_azbrowse = get_latest_azbrowse()
        logger.warn('Downloading latest azbrowse from {}'.format(latest_azbrowse))
        r = requests.get(latest_azbrowse, allow_redirects=True, stream=True)
        with open(azbrowse, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
        os.chmod(azbrowse, 0o755)

    logger.warn('Launching azbrowse, hit `Ctrl+C` to close')
    os.system(azbrowse)