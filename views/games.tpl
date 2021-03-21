%for g in all_games.order_by(lambda g: g.id):
    %url = "/static/empty.jpg"   
    %active = g.scenes.select(lambda s: s.id == g.active).first()
    %if active.backing is not None:
        %url = active.backing.url
    %end
    <div>
        <a href="{{server}}/{{gm.url}}/{{g.url}}" draggable="false" target="_blank"><img class="thumbnail" draggable="false" src="{{url}}" title="{{g.url.upper()}}" /></a>
        <div class="controls">
            <img class="icon" src="/static/cleanup.png" onClick="cleanUp('{{g.url}}');" draggable="false" title="CLEAN UP" />
            <a href="/vtt/export-game/{{g.url}}" draggable="false"><img class="icon" src="/static/export.png" draggable="false" title="EXPORT GAME" ></a>
            <img class="icon" src="/static/delete.png" onClick="deleteGame('{{g.url}}');" draggable="false" title="DELETE GAME" />
        </div>
    </div>
%end 
