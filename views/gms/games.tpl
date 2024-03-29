    %import time
    %now = time.time()
    %for g in all_games.order_by(lambda g: g.id):
        %url = "/vtt/thumbnail/" + '/'.join([g.gm_url, g.url])
        <div class="element">
            <a href="{{server}}/game/{{g.get_url()}}" draggable="false" target="_blank"><img class="thumbnail" draggable="false" src="{{url}}" title="{{g.url.upper()}}" /></a>
            <div class="controls">
                <img class="icon" src="/static/cleanup.png" onClick="cleanUp('{{g.url}}');" draggable="false" title="CLEAN UP" />
                <a href="/vtt/export-game/{{g.url}}" draggable="false"><img class="icon" src="/static/export.png" draggable="false" title="EXPORT GAME" ></a>
                <img class="icon" src="/static/delete.png" onClick="deleteGame('{{g.url}}');" draggable="false" title="DELETE GAME" />
        %if g.may_expire_soon(now):
                <span class="warning" title="MAY EXPIRE SOON">!</span>
        %end
            </div>
        </div>
    %end
