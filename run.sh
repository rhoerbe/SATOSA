#!/bin/bash

if [[ $1 == '-i' ]]; then # interactive
    docker rm -f satosa.rhdev 2>/dev/null
    cmd="docker run -it --rm -v /dv/satosa.rhdev:/opt/satosa/etc --net=host --cap-drop=all --name satosa.rhdev satosa.rhdev $2"
    echo $cmd
    $cmd
else   # background
    cmd="docker run -d --restart=unless-stopped  --net=host --cap-drop=all -v /dv/satosa.rhdev:/opt/satosa/etc --name satosa.rhdev satosa.rhdev"
    echo $cmd
    $cmd
fi