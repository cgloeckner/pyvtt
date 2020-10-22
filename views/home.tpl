%if is_gm:
	%include("header", title="Games List")

<div class="menu">

<h1>Games List</h1>

<table>
	%for g in games.order_by(lambda s: s.id):
	<tr>
		<td>{{g.url}}</td>
		<td><a href="/play/{{g.url}}" target="_blank">Join as GM</a></td>
		<td><a href="http://{{server}}/play/{{g.url}}" target="_blank">Join as Player</a></td>
	</tr>
	%end
</table>

<form action="/setup/create" id="create_game" method="post">
	Game title: <input type="text" name="game_url" value="my-game" /><input type="submit" value="Create" />
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
