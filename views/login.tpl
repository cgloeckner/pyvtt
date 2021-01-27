<div id="login">
	
%if user_agent is not None and 'mobile' in user_agent.lower():
	<div class="warning">
		<p>MOBILE DEVICES NOT SUPPORTED</p>
	</div>
%end
	
	<div class="menu">
		<hr />
		<h1>{{game.url.upper()}} by {{gm.name}}</h1>
		
		<img class="logo" src="/static/logo.png" />
		
		<div class="form">
			<form onsubmit="login(event, '{{gm.url}}', '{{game.url}}', '{{websocket_url}}');">
				<p>PLAYER NAME</p>
				<input type="text" name="playername" id="playername" autocomplete="off" value="{{playername}}" maxlength="30" />
				
				<p>PLAYER COLOR</p>
				<input type="color" name="playercolor" id="playercolor" value="{{playercolor}}">
				
				<p><input type="submit" id="loginbtn" value="JOIN" /></p>
			</form> 
		</div> 
		<hr />
	</div>  
</div>
