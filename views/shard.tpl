%include("header", title="Shards")

<div class="menu"> 

<hr />

<h1>SHARDS</h1>

<table class="status"> 
	<tr>
		<th></th>
		<th>URL</th>
		<th>CPU</th>
		<th>MEM</th>
		<th>PLAYERS</th>
	</tr>
%i = 0
%for host in engine.shards:
	<tr>
		<td id="flag{{i}}"></td>
	%if host == own:
		<td>{{host}}</td>
	%else:
		<td><a href="{{host}}/">{{host}}</a></td>
	%end
		<td id="cpu{{i}}">---</td>
		<td id="memory{{i}}">---</td>
		<td id="players{{i}}">---</td>
	</tr>
	%i += 1
%end 
</table>

<script>
function queryShard(index, host) {
	$.ajax({
		url: '/vtt/query/' + index,
		type: 'GET',
		success: function(response) {
			// show flag
			if (response.countryCode != null) {
				$('#flag' + index)[0].innerHTML = '<img src="https://www.countryflags.io/' + response.countryCode + '/flat/16.png" />';
			}
			
			// fallback output
			var cpu         = 'ERROR';
			var memory      = 'ERROR';
			var num_players = 'ERROR';
			
			// try to parse status
			try {
				data = JSON.parse(response.status);
				cpu         = data.cpu + '%';
				memory      = data.memory + '%';
				num_players = data.num_players;
			} catch (e) {
				console.warn('Server Status unknown: ', host);
			}
			
			// show result
			$('#cpu' + index)[0].innerHTML     = cpu;
			$('#memory' + index)[0].innerHTML  = memory;
			$('#players' + index)[0].innerHTML = num_players;
		}
	});
}
  
%i = 0
%for host in engine.shards:
queryShard({{i}}, '{{host}}');
	%i += 1
%end

</script>
<hr />

</div>

%include("footer")
