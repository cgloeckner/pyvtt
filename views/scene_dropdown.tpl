%import time, os

<div class="dropdown">
	<div id="preview">
		<img class="icon" src="/static/add.png" onClick="addScene();" />
%for s in game.scenes.order_by(lambda s: s.id):
	%t = s.getBackground()
	%url = "/static/empty.jpg"
	%if t is not None:
		%url = t.url
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
	</div>
	<img src="/static/menu.png" onClick="toggleDropdown();" />
</div>

