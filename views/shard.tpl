%include("header", title="Servers")

<div class="menu"> 

<hr />

<h1>SERVERS</h1>

<table class="status"> 
    <tr>
        <th class="small"></th>
        <th class="small"></th>
        <th class="medium"></th>
        <th>Link</th>
        <th>ACTIVE GAMES</th>
    </tr>
%i = 0
%for host in engine.shards:
    <tr>
        <td id="flag{{i}}"><img src="/static/loading.gif" /></td>
        <td><img src="{{host}}/static/favicon.ico" /></td>
        <td id="title{{i}}"><img src="/static/loading.gif" /></td>
    %if host == own:
        <td>{{host}}</td>
    %else:
        <td><a href="{{host}}/">{{host}}</a></td>
    %end
        <td id="games{{i}}"><img src="/static/loading.gif" /></td>
    </tr>
    %i += 1
%end 
</table>

<br />

<script>  
%i = 0
%for host in engine.shards:
queryShard({{i}}, '{{host}}');
    %i += 1
%end
</script>
<hr />

</div>

%include("footer")
