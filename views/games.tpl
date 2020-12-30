%for g in gm.games.order_by(lambda g: g.id):
	%url = "/static/empty.jpg"   
	%active = g.scenes.select(lambda s: s.id == g.active).first()
	%if active.backing is not None:
		%url = active.backing.url
	%end
	<div>
		<a href="{{server}}/{{g.admin.name}}/{{g.url}}" target="_blank"><img class="thumbnail" title="{{g.url}}" src="{{url}}" /></a>
		<div class="controls">                                     
			<img class="icon" src="/static/kick.png" onClick="kickPlayers('{{g.url}}');" />
			<a href="/vtt/export-game/{{g.url}}"><img class="icon" src="/static/export.png"></a>
			<img class="icon" src="/static/delete.png" onClick="deleteGame('{{g.url}}');" />
		</div>
	</div>
%end 
