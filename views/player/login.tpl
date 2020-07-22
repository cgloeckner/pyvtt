%include("header", title=game.active)

<h1>{{game.title}}</h1>

<form action="/login/{{game.title}}" method="post">
	Player Name: <input type="text" name="playername" /><input type="submit" value="Join" />
</form>

%include("footer")

