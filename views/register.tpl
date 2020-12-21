%include("header", title='Join as GM')

<div class="menu">

<h1>Join as GM</h1>

<form action="/vtt/register" method="post">
	<table>
		<tr>
			<td>GM-Name</td>
			<td><input type="text" name="gmname" /></td>
		</tr>
		<tr>
			<td>IP:</td>
			<td>{{ip}}</td>
		</tr>
		<tr>
			<td>
			<td><input type="submit" value="Start Campaign" /></td>
		</tr>
	</table>
</form>

<hr />

Are you a player? Ask your GM for the game link.

</div>

%include("footer")

