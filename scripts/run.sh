#!/bin/bash
PORT="8080"
VOLUME="/opt/pyvtt/prod"

usage() { echo "build.sh [-p PORT] [-v DIRECTORY] TAG [DOCKER COMMANDS]"; exit 0; }

[ $# -eq 0 ] && usage

while getopts ":hp:v:" arg; do
  case "${arg}" in
    p)
      PORT=${OPTARG}
      ;;
    v)
      VOLUME=${OPTARG}
      ;;
    h | *)
      usage
      exit 0
      ;;
  esac
done
# remove parsed optional arguments
shift $((OPTIND-1))
# get the tag, and remove it from arguments
TAG=$1; shift;

docker stop icvtt-${TAG}
docker rm icvtt-${TAG}
docker run -d -p ${PORT}:${PORT} -v ${VOLUME}:${VOLUME} --restart=on-failure --name icvtt-${TAG} pyvtt:${TAG} "$@"
