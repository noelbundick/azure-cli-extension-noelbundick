#!/bin/bash
set -euo pipefail

curl -sL https://aka.ms/InstallAzureCLIDeb | bash

apt-get install -y python3
python3 -m venv .venv

python -m pip install 'src/noelbundick[dev]'
pip install --upgrade --target ~/.azure/devcliextensions/noelbundick src/noelbundick