%include("header", title="Status")

<div class="menu"> 

<hr />

<h1>Server Status</h1>

<table class="status">  
	<tr>
		<th>CPU Load</th>
		<td>{{data['cpu_load']}}</td>
	</tr>
	<tr>
		<th>Memory Load</th>
		<td>{{data['memory_load']}}</td>
	</tr>
	<tr>
		<th>Image Cache</th>
		<td>{{data['img_size']}}</td>
	</tr>
	<tr>
		<th>Database Size</th>
		<td>{{data['db_size']}}</td>
	</tr>
	<tr>
		<td></td>
		<td><p><u>including:</u><br />
			{{data['num_gms']}} GMs<br />
			{{data['num_games']}} Games<br />
			{{data['num_scenes']}} Scenes<br />
			{{data['num_tokens']}} Tokens<br />
			{{data['num_rolls']}} Rolls
		</p></td>
	</tr>
	<tr>
		<th>Active Players</th>
		<td>{{data['num_players']}}</td>
	</tr>
</table>

<p>Queried within {{data['gen_time']}}s.</p>

</div>

%include("footer")
