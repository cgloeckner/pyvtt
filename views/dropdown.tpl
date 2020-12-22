%import time, os

	<img class="largeicon" src="/static/add.png" onClick="addScene();" />
%for s in game.scenes.order_by(lambda s: s.id):
	%url = "/static/empty.jpg"
	%if s.backing is not None:
		%url = s.backing.url
	%end
	%css = "thumbnail"
	%if game.active == s.id:
		%css = "active"
	%end
		<div>
			<img class="{{css}}" src="{{url}}" onClick="activateScene({{s.id}})" />
			<img class="icon" src="/static/copy.png" onClick="cloneScene({{s.id}});" />
			<img class="icon" src="/static/delete.png" onClick="deleteScene({{s.id}});" />
		</div>
%end
