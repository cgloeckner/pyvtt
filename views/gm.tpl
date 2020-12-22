%include("header", title="GM: {0}".format(gm.name))

<div class="menu" ondragover="GmUploadDrag(event);" ondrop="GmUploadDrop(event);">

<h1>GAMES by {{gm.name}}</h1>

	<div class="form">
		<p>ENTER GAME NAME</p>
		<input type="text" id="url" value="" /><br />
		<p><input type="button" onClick="createGame();" value="CREATE" /></p>
	</div>
	
%if len(gm.games) > 0:
	<p>PICK GAME</p>
	
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
%end

	<div class="form">
		<p>DRAG ARCHIVE TO IMPORT</p>
		<form id="uploadform" method="post" enctype="multipart/form-data">
			<input id="uploadqueue" name="file[]" type="file" multiple />
		</form>
	</div>
</div>

%include("footer")
