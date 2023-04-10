![Python application](https://github.com/cgloeckner/pyvtt/actions/workflows/python-app.yml/badge.svg?branch=master)

# pyvvt
Python-based Virtual Tabletop Tool

## What is this?

This piece of software is the engine behind the [Index Card Virtual Tabletop (ICVTT)](https://icvtt.net). It's mostly designed for playing variations of _Index Card RPG_ (ICRPG) by [Runehammer Games](http://runehammer.online) but can be used with other tabletop games (like _WAR|MAKER_, also by Runehammer Games).

See the wiki for more details.

# Docker
This application includes a simple Dockerfile to build a runnable container.

`./script/build.sh` will build an image for you. This script accepts one optional parameter: a tag to apply to the resultant image. If no tag is specified, `latest` will be used.

`./script/run.sh` will (re)start the image. It takes three optional parameters: the tag to use, the port to use, and the path to the location to mount into the container. The default values are `latest`, `8080`, and `/opt/pyvtt/prod` respectively.

## Contributions

Kane Driscol
- Lead Artist (see commit details)
- Community Manager for ICVTT over on the [Runehammer Forums](https://forums.runehammer.online/) and [ICRPG Discord Community](https://discord.gg/H76tfBZZEX)

Coyote
- Majority of default assets

Ryan C. Scott
- help on setting up `nginx` reverse proxy

Scott Merrill
- Server Admin for [ICVTT](https://icvtt.net)
- docker-related things and more

