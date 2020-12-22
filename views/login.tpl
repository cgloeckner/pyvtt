%include("header", title='Login: {0} by {1}'.format(game.url.upper(), game.admin.name))

<div class="menu">

<h1>{{game.url.upper()}} by {{game.admin.name}}</h1>

<form action="/{{game.admin.name}}/{{game.url}}/login" method="post" enctype="multipart/form-data">
	<p>PLAYER NAME</p>
	<input type="text" name="playername" value="{{playername}}" />
	
	<p>PLAYER COLOR</p>
	<input type="color" name="playercolor" onchange="clickColor(0, -1, -1, 5)" value="{{color}}">
	
	<p><input type="submit" value="JOIN" /></p>
</form>

</div>

%include("footer")

