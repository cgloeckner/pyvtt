%include("header", title='JOIN as GM')

<div class="menu">

<hr />

<h1>JOIN as GM</h1>

<img class="logo" src="/static/logo.png" />

<div class="form">
	<form onsubmit="registerGm(event);">
		<p>GM NAME</p>
		<input type="text" id="gmname" maxlength="20" autocomplete="off" value="{{playname}}" />
		
		<p><input type="submit" value="START CAMPAIGN" /></p>
	</form>
</div>


Are you a player? Ask your GM for the game link.

<hr />

</div>

%include("footer")

