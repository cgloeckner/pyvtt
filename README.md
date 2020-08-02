# pyvvt
Python-based Virtual Tabletop Tool

requires pony (DB) and paste (async HTTP)

# Planned features/fixes
- synchronous db-access
- implement INSERT (clone selected to mouse pos), DEL (deleted selected)

# How to run
- start `main.py` on GM's local computer
- enable portforwarding for port 8080 for this computer in your router
- query your public IP, set up your game in the browsre
- send the players-link to your players to join

# Known bugs
- random player timeouts using microsoft edge
- instant player timeout using mobile devices
- unable to move tokens using mobile devices

