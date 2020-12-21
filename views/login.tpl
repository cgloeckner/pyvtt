%include("header", title='Login: {0} by {1}'.format(game.url, game.admin.name))

<div class="menu">

<h1>{{game.url.upper()}} by {{game.admin.name}}</h1>

<form action="/{{game.admin.name}}/{{game.url}}/login" method="post" enctype="multipart/form-data">
	<table>
		<tr>
			<td>NAME</td>
			<td><input type="text" name="playername" value="{{playername}}" /></td>
		</tr>
		<tr>
			<td>COLOR</td>
			<td><input type="color" name="playercolor" onchange="clickColor(0, -1, -1, 5)" value="{{color}}"></td>
		</tr>
		<tr>
			<td>
			<td><input type="submit" value="JOIN" /></td>
		</tr>
</form>

</div>

%include("footer")

