Later version might include WebSockets

`pip3 install bottle-websocket`

`main.py`
```python
#!/usr/bin/python3

from bottle import *

@route('/')
@view('index')
def test():
	return dict()

@route('/websocket')
def handle_websocket():
	wsock = request.environ.get('wsgi.websocket')
	if not wsock:
		abort(400, 'Expected WebSocket request.')
	while True:
		try:
			message = wsock.receive()
			print(message)
			wsock.send("Your message was: %r" % message)
		except WebSocketError:
			break

from bottle.ext.websocket import GeventWebSocketServer
from bottle.ext.websocket import websocket

run(host='localhost', port=8080, server=GeventWebSocketServer)
```

`index.tpl`
```html
<!DOCTYPE html>
<html>
<head>
<script type="text/javascript">

var ws = new WebSocket("ws://localhost:8080/websocket");

ws.onopen = function() {
	ws.send("Hello, world");
};

ws.onmessage = function (evt) {
	alert(evt.data);
};

</script>
</head>
</html>
```

Requires in-depth reworking of communication
- developing protocol (with `cmd` and other data via JSON)
- server sided exception handling (`KeyError` etc.)
- thread per websocket handler (aka ClientHandler)
- linking between ClientHandlers to notify on changes (e.g. login)
