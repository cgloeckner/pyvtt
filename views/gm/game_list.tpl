%include("header", title="Games List")

<div class="menu">

<h1>Games List</h1>

<table>
%for g in games.order_by(lambda s: s.id):
	<tr>
		<td>{{g.title}}</td>
		<td><a href="/setup/list/{{g.title}}">Setup</a></td>
		%if g.active != '':
			<td><a href="/play/{{g.title}}" target="_blank">Play</a></td>
		%else:
			<td></td>
			<td></td>
		%end
	</tr>
%end
</table>

<form action="/setup/create" id="create_game" method="post">
	Game title: <input type="text" name="game_title" value="untitled" /><input type="submit" value="Create" />
</form>

</div>

%include("footer")

