%include("header", title="[GM] {0}".format(game.title))

<h1>Setup Game: {{game.title}}</a></h1>
%if game.active != '':
<a href="/gm/{{game.title}}">Play as GM</a> - <a href="/play/{{game.title}}">Player-Link</a>
%end

<h2>Available Scenes:</h2>
<ul>
%for s in game.scenes:
	<li>{{s.title}} - <a href="/activate/{{game.title}}/{{s.title}}">Activate</a></li>
%end
</ul>

<b>Active Scene</b>: {{game.active}}

<form action="/create_scene/{{game.title}}" id="create_scene" method="post">
	Create Scene with Title: <input type="text" name="scene_title" value="untitled" /><input type="submit" value="Create" />
</form>

<a href="/">Back to Games Overview</a>

<hr />

<a href="/delete/{{game.title}}">Delete</a>

%include("footer")

