%include("header", title="Games List")

<h1>Games</h1>

<ul>
%for title in games:
	<li><a href="/setup/{{title}}">{{title}}</a></li>
%end
</ul>

<form action="/create_game/" id="create_game" method="post">
	Game title: <input type="text" name="game_title" value="untitled" /><input type="submit" value="Create" />
</form>

%include("footer")

