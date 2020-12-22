<div id="login" class="menu">
	<div>
		<h1>{{game.url.upper()}} by {{game.admin.name}}</h1>

		<form>
			<p>PLAYER NAME</p>
			<input type="text" name="playername" id="playername" value="{{playername}}" />
			
			<p>PLAYER COLOR</p>
			<input type="color" name="playercolor" id="playercolor" value="{{playercolor}}">
			
			<p><input type="button" value="JOIN" onClick="login('{{game.url}}', '{{is_gm}}', '{{game.admin.name}}', '{{game.multiselect}}')"; /></p>
		</form>
	</div>
</div>
