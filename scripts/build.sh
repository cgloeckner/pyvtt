#!/bin/bash
SHA=$(git rev-parse HEAD)
docker build -t pyvtt:${SHA} .
docker tag pyvtt:${SHA} pyvtt:latest
