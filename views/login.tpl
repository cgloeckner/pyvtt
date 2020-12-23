<div id="login">
	<div class="menu">
		<hr />
		<h1>{{game.url.upper()}} by {{game.admin.name}}</h1>
		
		<img class="logo" src="/static/logo.png" />

		<div class="form">
			<p>PLAYER NAME</p>
			<input type="text" name="playername" id="playername" value="{{playername}}" maxlength="18" />
			
			<p>PLAYER COLOR</p>
			<input type="color" name="playercolor" id="playercolor" value="{{playercolor}}">
			
			<p><input type="button" value="JOIN" onClick="login('{{game.url}}', '{{game.admin.name}}')"; /></p>
		</div> 
		<hr />
	</div>  
</div>
