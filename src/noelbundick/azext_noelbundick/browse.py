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
    is_current = False
    
    latest_azbrowse = get_latest_azbrowse()
    azbrowse = os.path.join(get_config_dir(), 'azbrowse')

    if os.path.isfile(azbrowse):
        match = re.search('https://github.com/lawrencegripper/azbrowse/releases/download/v(?P<version>.*)/(.*)', latest_azbrowse)
        latest_version = match.group('version')
        current_version = subprocess.check_output([azbrowse, 'version']).decode("utf-8").strip()

        logger.info('Current azbrowse: {}, Latest azbrowse: {}'.format(current_version, latest_version))
        if latest_version == current_version:
            is_current = True
    
    if not is_current:
        logger.warn('Downloading latest azbrowse from {}'.format(latest_azbrowse))
        executable = os.path.join(get_config_dir(), 'azbrowse')
        r = requests.get(latest_azbrowse, allow_redirects=True, stream=True)
        with open(executable, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
        os.chmod(executable, 0o755)

    logger.warn('Launching azbrowse, hit `Ctrl+C` to close')
    os.system(azbrowse)