# pyvvt
Python-based Virtual Tabletop Tool

requires pony (DB) and paste (async HTTP)

# How to run
- start `main.py` on GM's local computer
- enable portforwarding for port 8080 for this computer in your router
- query your public IP, set up your game in the browser
- send the play-link to your players to join
- Recommended browser: Firefox (non-mobile device)

# GM not local?
start with `--lazy` to skip IP-checking for GM-routes

# Development notes
start with `--debug` to start in auto-reloading (but non-threaded) dev mode (localhost only)

# Known bugs
- edge: extreme slow ajax
- opera: extreme slow page loading
- mobile: cannot grab token (-.-)
- no proper logout if the browser is completly closed
