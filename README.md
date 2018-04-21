# Noel's grab bag of Azure CLI goodies

This repo contains things that I like or find useful, offered up with absolutely zero guarantee that it will work for anyone else

## Features

### Log Analytics - List workspace keys

Usage:

```bash
az loganalytics workspace keys list -n myworkspace -g myresourcegroup
```

Output:

```json
{
  "primarySharedKey": "EQEDQ+kmMlqiavat9HMa4ZrPDrAs1P6c6ZcQDY+WY3x9Qy3gapo+7UhzZT2UwCvhg5sfp65hhGjpFm8ljXB7+w==",
  "secondarySharedKey": "Vj95R5kIRICkzFVHAS+j2tVBiXsBLlNNEzJa8A1vgD7CkeI7MTbOTUAs8sy3RLV+n2KDbhA+iQHw3kd5BhhevA=="
}
```

## Development

```bash
export AZURE_EXTENSION_DIR=~/.azure/devcliextensions
pip install --upgrade --target ~/.azure/devcliextensions/noelbundick ~/code/noelbundick/azure-cli-extension-noelbundick
```