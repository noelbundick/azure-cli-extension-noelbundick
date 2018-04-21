#!/bin/sh

DIR=$(dirname $0)
SRC="${DIR}/../src/noelbundick/setup.py"
DEST="${DIR}/../dist"
python $SRC bdist_wheel -d $DEST