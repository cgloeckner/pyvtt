%include("header", title='{0} (Login)'.format(game.title))

<div class="menu">

<h1>{{game.title}}</h1>

<form action="/login/{{game.title}}" method="post">
	Player Name: <input type="text" name="playername" /><input type="submit" value="Join" />
</form>

</div>

%include("footer")

