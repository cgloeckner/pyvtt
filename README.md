# pyvvt
Python-based Virtual Tabletop Tool

Recommended Browser: Firefox (non-mobile device, at least at the moment)

# I want to host it myself
Start `vtt.py` on your machine (currently only Linux-based OS are supported, this may change in future ... idk). Make sure to enable port forwarding for port 8080 (or specify another port via `--port=80` when starting) for this computer in your router.
If you are hosting using your public IP, consider setting starting the server with `--local-gm` and set up your games via `localhost`. Launching with `--local-gm` will replace all `http://localhost` in the game-links by your public IP, so you can easily copy and paste those to your players. If you setup your games with your public IP, your game data can get unaccessable if your IP changes (because cookies are bound to the server name or in this case IP address).
*Note:* Requires `bottle` (as HTTP server), `gevent` (for async HTTP) and `pony` (as database ORM). Consider using `pip` or similar tools.

# Running with nginx through unix socket
Customize your nginx configuration and run it:
```
nginx -c /path/to/vtt-nginx.conf
```
Consider updating PyVTT's configuration at `~/.local/share/pyvtt/settings.json`, for example add a value to `socket` matching your nginx-settings:
```
{
	"title": "My Custom VTT",
	"imprint": {
		"label": "Terms & Contact",
		"url": "/static/terms.html"
	},
	"host": "play.mydomain.com",
	"port": 80,
	"socket": "/tmp/vtt.sock"
}
```
Finally just run PyVTT
```
./vtt.py
```

Optional settings parameters are `expire` (seconds until a GM or game can be picked up by the `cleanup.py` script) and `ssl`. Put your `cacert.pem` and `privkey.pem` inside `~/.local/share/pyvtt/ssl`.

Create SSL certificate and private key for testing:
```openssl req -new -x509 -days 1095 -nodes -newkey rsa:2048 -out cacert.pem -keyout privkey.pem```

# GM Information
Access your the via your Browser. There is no real login but every GM is identified with your GM-name (entered) and a session ID (generated and stored in a cookie). Once you clear your cookies, you lose access to your games. But wait, there is more.
You can export set-up games as ZIP files, which can be downloaded on your computer. They contain all scenes and images (including positions, rotations etc.). So you can easily reimport a previous game if you want.

# Player Information
Ask for a link and start playing. Make sure to enable JavaScript and allow Cookies.

# Debugging
`update_cycles` (`default: 30`) can be adjusted in the browser client (e.g. via developer tools CTRL+SHIFT+I).

# Cleanup
To cleanup the database from expired records, stop the VTT, run `cleanup.py` and restart the VTT then.

# Known bugs
(may not be up to date)
- edge: extreme slow ajax
- opera: extreme slow page loading
- mobile: cannot grab token (-.-)
- no proper logout if the browser is completly closed
