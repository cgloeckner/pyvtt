%include("header", title="GM {0}".format(gm.name))

<div class="menu">

<hr />

<h1>GAMES by {{gm.name}}</h1>
 
	<div class="form">
		<form onsubmit="createGame(event);">
			<p>ENTER GAME NAME</p>
			<input type="text" id="url" value="{{generated_url}}" /><br />
			<p><input type="submit" value="CREATE" /></p>
		</form>
	</div>

<hr />

</div>

%include("footer")
