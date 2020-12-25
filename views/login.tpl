<div id="login">
	<div class="menu">
		<hr />
		<h1>{{game.url.upper()}} by {{game.admin.name}}</h1>
		
		<img class="logo" src="/static/logo.png" />

		<div class="form">
			<form onsubmit="login(event, '{{game.url}}', '{{game.admin.name}}');">
				<p>PLAYER NAME</p>
				<input type="text" name="playername" id="playername" value="{{playername}}" maxlength="18" />
				
				<p>PLAYER COLOR</p>
				<input type="color" name="playercolor" id="playercolor" value="{{playercolor}}">
				
				<p><input type="submit" value="JOIN" /></p>
			</form>
		</div> 
		<hr />
	</div>  
</div>
