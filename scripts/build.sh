#!/bin/bash
TAG="${1:-latest}"
SHA=$(git rev-parse HEAD)
echo ${SHA} > sha.txt
echo docker build -t pyvtt:${SHA} .
echo docker tag pyvtt:${SHA} pyvtt:${TAG}
