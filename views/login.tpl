%include("header", title='Login: {0}'.format(game.url))

<div class="menu">

<h1>{{game.url}}</h1>

<form action="/play/{{game.url}}/login" method="post">
	<table>
		<tr>
			<td>Name</td>
			<td><input type="text" name="playername" /></td>
		</tr>
		<tr>
			<td>Color</td>
			<td><input type="color" name="playercolor" onchange="clickColor(0, -1, -1, 5)" value="{{color}}"></td>
		</tr>
		<tr>
			<td>
			<td><input type="submit" value="Join" /></td>
		</tr>
</form>

</div>

%include("footer")

