%for g in all_games.order_by(lambda g: g.id):
    %url = "/static/empty.jpg"   
    %active = g.scenes.select(lambda s: s.id == g.active).first()
    %if active.backing is not None:
        %url = active.backing.url
    %end
    <div>
        <a href="{{server}}/{{gm.url}}/{{g.url}}" draggable="false" target="_blank"><img class="thumbnail" title="{{g.url}}" draggable="false" src="{{url}}" onMouseEnter="showHint(event, '{{g.url.upper()}}');" onMouseLeave="hideHint();" /></a>
        <div class="controls">
            <img class="icon" src="/static/kick.gif" onClick="kickPlayers('{{g.url}}');" draggable="false" onMouseEnter="showHint(event, 'KICK PLAYERS');" onMouseLeave="hideHint();" />
            <a href="/vtt/export-game/{{g.url}}" draggable="false"><img class="icon" src="/static/export.png" draggable="false"onMouseEnter="showHint(event, 'EXPORT GAME');" onMouseLeave="hideHint();" ></a>
            <img class="icon" src="/static/delete.png" onClick="deleteGame('{{g.url}}');" draggable="false" onMouseEnter="showHint(event, 'DELETE GAME');" onMouseLeave="hideHint();" />
        </div>
    </div>
%end 
