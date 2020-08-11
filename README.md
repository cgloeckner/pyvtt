# pyvvt
Python-based Virtual Tabletop Tool

requires pony (DB) and paste (async HTTP)

# Planned features/fixes
- synchronous db-access

# How to run
- start `main.py` on GM's local computer
- enable portforwarding for port 8080 for this computer in your router
- query your public IP, set up your game in the browser
- send the players-link to your players to join

Recommended browser: Firefox

# Known bugs
- edge: extreme slow ajax
- opera: extreme slow page loading
- mobile: scrolling issue (various browsers)
- no proper logout if the browser is completly closed

