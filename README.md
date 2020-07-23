# pyvvt
Python-based Virtual Tabletop Tool


# Planned features/fixes
- fix scene cloning (cloned scene seems empty, looks like a query error)
- cleanup routes (/play/.., /gm/... and /setup/... only) --> restrict cookie path, too
- Improve Rolling Dice (better log, less buggy, auto-scroll)
- Layout improvements (remove borders, set background color etc.)
- Player Names (add GM to playerlist, list players, handle timeout via keepalive via update pull)
- multithreading server + synchronous db-access
- implement CTRL+C, CTRL+V, CTRL+A, DEL key behavior
