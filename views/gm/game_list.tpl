%include("header", title="Games List")

<h1>Games</h1>

<ul>
%for g in games:
	<li><a href="/setup/{{g.title}}">{{g.title}}</a></li>
%end
</ul>

<form action="/create_game/" id="create_game" method="post">
	Game title: <input type="text" name="game_title" value="untitled" /><input type="submit" value="Create" />
</form>

%include("footer")

