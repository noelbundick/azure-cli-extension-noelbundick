#!/bin/bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
azdev setup -r . -e noelbundick
