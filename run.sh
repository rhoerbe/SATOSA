#!/bin/bash

docker run -it --rm -v satosa.rh_dev:/opt/satosa/etc --name satosa.rhdev satosa.rhdev $1
