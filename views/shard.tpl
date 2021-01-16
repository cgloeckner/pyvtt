%include("header", title="Servers")

<div class="menu"> 

<hr />

<h1>{{engine.title}} SERVERS</h1>

<table class="status"> 
	<tr>
		<th></th>
		<th>SERVER</th>
		<th>STATUS</th>
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
		<td id="status{{i}}">UNKNOWN</td>
		<td id="players{{i}}">UNKNOWN</td>
	</tr>
	%i += 1
%end 
</table>

<br />

<script>
function queryShard(index, host) {
	var now = Date.now()
	
	$.ajax({
		url: '/vtt/query/' + index,
		type: 'GET',
		success: function(response) {
			// show flag
			if (response.countryCode != null) {
				$('#flag' + index)[0].innerHTML = '<img src="https://www.countryflags.io/' + response.countryCode + '/flat/16.png" />';
			}
			
			// fallback output
			var color   = 'red'
			var status  = 'OFFLINE';
			var hint    = 'Please report this';
			var players = 'UNKNOWN'
			
			// try to parse status
			try {
				data = JSON.parse(response.status);
				if (data.cpu > 90.0 || data.memory > 90.0) {
					color  = 'orange';
					status = 'VERY BAD';
				} else if (data.cpu > 80.0 || data.memory > 80.0) {
					color  = 'orange';
					status = 'BAD';
				} else if (data.cpu > 40.0 || data.memory > 40.0) {
					color  = 'yellow';
					status = 'OK';
				} else if (data.cpu > 10.0 || data.memory > 10.0) {
					color  = 'green';
					status = 'GOOD';
				} else {
					color  = 'green';
					status = 'VERY GOOD';
				}
				hint    = data.cpu + '% CPU\n' + data.memory + '% Memory';
				players = data.num_players;
			} catch (e) {
				console.warn('Server Status unknown: ', host);
			}
			
			// show result
			$('#status' + index)[0].innerHTML = '<span style="color: ' + color + '" title="' + hint + '">' + status + '</span>';
			$('#players' + index)[0].innerHTML = '<span style="color: ' + color + '">' + players + '</span>';
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
