%include("header", title="Games List")

<h1>Games Overview</h1>

<ul>
%for g in games:
	<li>{{g.title}} - <a href="/setup/list/{{g.title}}">Setup</a>
	%if g.active != '':
	 - <a href="/gm/{{g.title}}" target="_blank">Play as GM</a> - <a href="/play/{{g.title}}"  target="_blank">Player-Link</a></li>
	%end
%end
</ul>

<form action="/setup/create/" id="create_game" method="post">
	Game title: <input type="text" name="game_title" value="untitled" /><input type="submit" value="Create" />
</form>

%include("footer")

