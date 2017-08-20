#!/bin/bash

# interactive
docker run -it --rm -v satosa.rh_dev:/opt/satosa/etc --net=host --name satosa.rhdev satosa.rhdev $1

# background
# docker run -d --restart=unless-stopped  ---net=host v satosa.rh_dev:/opt/satosa/etc --name satosa.rhdev satosa.rhdev

# --cap-drop=all --cap-add=net_raw
