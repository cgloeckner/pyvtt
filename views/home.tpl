%if is_gm:
	%include("header", title="Games List")

<div class="menu">

<h1>Games List</h1>

	<div id="preview">
%for g in games.order_by(lambda g: g.id):
	%s = dbScene.select(lambda s: s.id == g.active).first()
	%url = "/static/empty.jpg"
	%if s.backing is not None:
		%url = s.backing.url
	%end
	%print(url)
		<div>
			<p>{{g.url}} <a href="/setup/delete/{{g.url}}"><img class="icon" src="/static/delete.png" /></a></p>
			<a href="/play/{{g.url}}" target="_blank"><img class="thumbnail" src="{{url}}" /></a><br />
			Public Link: <a href="http://{{server}}/play/{{g.url}}" target="_blank">here</a><br />
		</div>
%end
	</div>

	<br />

	<form action="/setup/create" id="create_game" method="post">
		http://{{server}}/play/<input type="text" name="game_url" value="my-game" /><input type="submit" value="Create" />
	</form>

	<br />

</div>
%else:
	%include("header", title="PyVTT")
	
<div class="menu">

	<h1>Welcome</h1>

	Are you a player? Ask your GM for the game link.
	<br />
	&nbsp;

</div>
%end

%include("footer")
