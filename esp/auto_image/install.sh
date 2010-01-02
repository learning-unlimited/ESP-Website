#!/bin/sh

DIRNAME=`dirname "$0"`

cp -v $DIRNAME/build/*.png "$DIRNAME/../public/media/images/theme/gen/"

cp -v "$DIRNAME/build/theme.css" "$DIRNAME/../public/media/styles/theme-gen.css"
