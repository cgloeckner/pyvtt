# pyvvt
Python-based Virtual Tabletop Tool

requires pony (DB) and paste (async HTTP)

# How to run
- start `main.py` on GM's local computer
- enable portforwarding for port 8080 for this computer in your router
- query your public IP, set up your game in the browser
- send the play-link to your players to join

# GM not local?
start with `--lazy` to skip IP-checking for GM-routes

Recommended browser: Firefox

# Known bugs
- edge: extreme slow ajax
- opera: extreme slow page loading
- mobile: scrolling issue (various browsers)
- no proper logout if the browser is completly closed
