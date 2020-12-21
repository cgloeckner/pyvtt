%include("header", title="GM: {0}".format(gm.name))

<div class="menu">

<h1>GAMES by {{gm.name}}</h1>

	<div id="preview">
%for g in gm.games.order_by(lambda g: g.id):
	%s = dbScene.select(lambda s: s.id == g.active).first()
	%url = "/static/empty.jpg"
	%if s.backing is not None:
		%url = s.backing.url
	%end
		<div>
			<p>
				<a href="/vtt/modify-game/{{g.url}}"><img class="icon" src="/static/modify.png"></a> <a href="/vtt/export-game/{{g.url}}"><img class="icon" src="/static/export.png"></a>
				{{g.url.upper()}}
				<a href="/vtt/delete-game/{{g.url}}"><img class="icon" src="/static/delete.png" /></a>
			</p>
				<a href="{{server}}/{{g.admin.name}}/{{g.url}}" target="_blank"><img class="thumbnail" src="{{url}}" /></a><br />
		</div>
%end
	</div>

	<br />

	<form action="/vtt/create-game" id="create_game" method="post" enctype="multipart/form-data">
		LINK {{server}}/{{gm.name}}/<input type="text" name="game_url" value="my-game" /><input type="submit" value="CREATE" /><br />
		IMPORT <input type="file" name="archive" />
	</form>

	<br />
</div>

%include("footer")
