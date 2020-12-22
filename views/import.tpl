%include("header", title="GM: {0}".format(gm.name))

<div class="menu">

<h1>IMPORT for {{url.upper()}} by {{gm.name}}</h1>
	
	<form action="/vtt/import-game/{{url}}" id="create_game" method="post" enctype="multipart/form-data">
		<input type="file" name="archive" /><input type="submit" name="button" value="IMPORT" />
	</form>
</div>

%include("footer")
