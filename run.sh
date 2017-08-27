#!/bin/bash

if [[ $1 == '-i' ]]; then # interactive
    cmd="docker run -it --rm -v satosa.rh_dev:/opt/satosa/etc --net=host --cap-drop=all --name satosa.rhdev satosa.rhdev $2"
    echo $cmd
    $cmd
else   # background
    cmd="docker run -d --restart=unless-stopped  --net=host --cap-drop=all -v satosa.rh_dev:/opt/satosa/etc --name satosa.rhdev satosa.rhdev"
    echo $cmd
    $cmd
fi