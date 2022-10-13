#!/bin/bash
docker stop icvtt
docker rm icvtt
docker run -d -p 8080:8080 -v /opt/pyvtt/prod:/opt/pyvtt/prod --restart=on-failure --name icvtt pyvtt:latest
