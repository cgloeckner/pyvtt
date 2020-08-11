%from random import randrange
%include("header", title='Login: {0}'.format(game.title))

<div class="menu">

<h1>{{game.title}}</h1>

<form action="/login/{{game.title}}" method="post">
	<table>
		<tr>
			<td>Name</td>
			<td><input type="text" name="playername" /></td>
		</tr>
		<tr>
			<td>Color</td>
%#pick random color:
%colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff']
%k = randrange(len(colors))
			<td><input type="color" name="playercolor" onchange="clickColor(0, -1, -1, 5)" value="{{colors[k]}}"></td>
		</tr>
		<tr>
			<td>
			<td><input type="submit" value="Join" /></td>
		</tr>
</form>

</div>

%include("footer")

