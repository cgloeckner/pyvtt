#!/bin/bash
TAG="${1:-latest}"
SHA=$(git rev-parse --short HEAD)
echo ${SHORT} > sha.txt
docker build -t pyvtt:${SHA} .
docker tag pyvtt:${SHA} pyvtt:${TAG}
