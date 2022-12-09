#!/bin/bash
TAG="${1:-latest}"
SHA=$(git rev-parse --short HEAD)
echo "${SHA}" > sha.txt
docker build -t pyvtt:"${SHA}" .
docker tag pyvtt:"${SHA}" pyvtt:"${TAG}"
