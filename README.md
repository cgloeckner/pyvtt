![Python application](https://github.com/cgloeckner/pyvtt/workflows/Python%20application/badge.svg?branch=master)

# pyvvt
Python-based Virtual Tabletop Tool

## What is this?

This piece of software is meant to be a easy-to-use, no-tutorial implementation of a Virtual Tabletop (VTT). Its mostly designed for playing variations of _Index Card RPG_ (ICRPG) and _WAR|MAKER_ by [Runehammer Games](http://runehammer.online). But it can also be used for Dungeons & Dragons etc.

See the wiki for more details.

## Dev environment setup

0. Install [Poetry](https://python-poetry.org)
1. `poetry install` (or `poetry install --no-dev` for production build)
2. `poetry shell`

Then you can do everything as usual inside a python virtual environment. Run `deactivate` to get out of it

Use `poetry` to install and update dependencies: `poetry add`/`poetry update`

## Credits

- `dicetray.png` by Kane Driscol
- fixes for nginx proxy by Ryan C. Scott
