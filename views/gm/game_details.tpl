%include("header", title=game.title)

<h1>Setup Game: {{game.title}}</a></h1>
%if game.active != '':
<a href="/gm/{{game.title}}" target="_blank">Play as GM</a> - <a href="/play/{{game.title}}" target="_blank">Player-Link</a>
%end

<form action="/gm/{{game.title}}/create" id="create" method="post">
	Create Scene with Title: <input type="text" name="scene_title" value="untitled" />
	<input type="submit" value="Create" />
</form>

<h2>Available Scenes:</h2>
<table>
%for s in game.scenes.order_by(lambda s: s.id):
	<tr>
		<td>{{s.title}}</td>
		<td><a href="/gm/{{game.title}}/activate/{{s.title}}">Activate</a></td>
		<td><a href="/gm/{{game.title}}/clone/{{s.title}}">Duplicate</a></td>
		<td><form action="/gm/{{game.title}}/rename/{{s.title}}" id="rename_{{s.id}}" method="post">
				<input type="text" name="scene_title" value="" />
				<input type="submit" value="Rename" />
		</form></td>
		<td><a href="/gm/{{game.title}}/delete/{{s.title}}">Delete</a></td>
	</tr>
%end
</table>

<b>Active Scene</b>: {{game.active}}

<h2>Available Players:</h2>
<table>
	<tr>
		<td>GM</td>
		<td>-</td>
		<td></td>
	</tr>
%for p in game.players.order_by(lambda p: p.name):
	<tr>
		<td>{{p.name}}</td>
		<td>{{p.alive}}</td>
		<td><a href="/gm/{{game.title}}/kick/{{p.name}}">Kick</a></td>
	</tr>
%end
</table>

<a href="/">Back to Games Overview</a>

<hr />

<a href="/setup/delete/{{game.title}}">Delete Game</a>

%include("footer")

