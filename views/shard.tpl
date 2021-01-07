%include("header", title="Shards")

<div class="menu"> 

<hr />

<h1>SHARDS</h1>

<table class="status"> 
	<tr>
		<th>URL</th>
		<th>CPU</th>
		<th>MEM</th>
		<th>PLAYERS</th>
	</tr>
%i = 0
%for host in engine.shards:
	<tr>
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
			try {
				data = JSON.parse(response);
				
				$('#cpu' + index)[0].innerHTML     = data.cpu + '%';
				$('#memory' + index)[0].innerHTML  = data.memory + '%';
				$('#players' + index)[0].innerHTML = data.num_players;
			} catch (e) {
				console.warn('Server Status unknown: ', host);
				
				var msg = 'ERROR';
				$('#cpu' + index)[0].innerHTML     = msg;
				$('#memory' + index)[0].innerHTML  = msg;
				$('#players' + index)[0].innerHTML = msg;
			}
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
