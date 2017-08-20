#!/bin/bash

# interactive
#docker run -it --rm -v satosa.rh_dev:/opt/satosa/etc --net=host --cap-drop=all --name satosa.rhdev satosa.rhdev $1

# background
docker run -d --restart=unless-stopped  --net=host --cap-drop=all -v satosa.rh_dev:/opt/satosa/etc --name satosa.rhdev satosa.rhdev
