#!/bin/sh

# Must be run from src/noelbundick/setup.py as working dir

DIR=$(dirname $0)
SRC="${DIR}/../src/noelbundick/setup.py"
DEST="${DIR}/../dist"
python $SRC bdist_wheel -d $DEST
