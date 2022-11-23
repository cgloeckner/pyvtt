#!/bin/bash
if [ $1 = "-h" ]; then
  echo "build.sh [TAG] [PORT] [MOUNT]"
  exit 0;
fi

TAG="${1:-latest}"
PORT="${2:-8080}"
MOUNT="${3:-/opt/pyvtt/prod}"
docker stop icvtt-${TAG}
docker rm icvtt-${TAG}
docker run -d -p ${PORT}:${PORT} -v ${MOUNT}:${MOUNT} --restart=on-failure --name icvtt-${TAG} pyvtt:${TAG}
