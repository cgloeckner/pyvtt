%include("header", title="Servers")

<div class="menu"> 

<hr />

<h1>SERVERS</h1>

<table class="status"> 
    <tr>
        <th></th>
        <th>SERVER</th>
        <th>STATUS</th>
        <th>GAMES</th>
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
        <td id="games{{i}}">UNKNOWN</td>
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
            if (response.flag != null) {
                $('#flag' + index)[0].innerHTML = response.flag;
            }
            
            // fallback output
            var color  = 'red'
            var status = 'OFFLINE';
            var hint   = 'Please report this';
            var games  = 'UNKNOWN'

            // try to parse status
            try {
                data   = JSON.parse(response.status);
                color  = 'green'
                status = 'ONLINE'
                hint   = 'Trouble? E-Mail us!'
                games  = data.games.running
            } catch (e) {
                console.warn('Server Status unknown: ', host);
            }
            
            // show result
            $('#status' + index)[0].innerHTML = '<span style="color: ' + color + '" title="' + hint + '">' + status + '</span>';
            $('#games' + index)[0].innerHTML = '<span style="color: ' + color + '">' + games + ' RUNNING</span>';
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
