%include("header", title="[GM] {0}".format(game.title))

<h1>Setup Game: 
%if game.active != '':
	<a href="/play/{{game.title}}">{{game.title}}</a>
%else:
	{{game.title}}
%end
</h1>
<a href="/delete/{{game.title}}">Delete</a>

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

%include("footer")

