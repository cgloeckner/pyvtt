%include("header", title="[GM] {0}".format(game.title))

<h1><a href="/play/{{game.title}}">{{game.title}}</a></h1>

<ul>
%for s in game.scenes:
	<li><a href="/setup/{{game.title}}/{{s.title}}">{{s.title}}</a></li>
%end
</ul>

active: {{game.active}}

<form action="/create_scene/{{game.title}}" id="create_scene" method="post">
	Scene title: <input type="text" name="scene_title" value="untitled" /><input type="submit" value="Create" />
</form>

%include("footer")

