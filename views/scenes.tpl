    <img class="largeicon" src="/static/add.png" onClick="addScene();" draggable="false" title="CREATE SCENE" />
%for s in game.scenes.order_by(lambda s: s.id):
    %url = "/static/empty.jpg"
    %if s.backing is not None:
        %url = s.backing.url
    %end
    %css  = "thumbnail"
    %hint = "SWITCH TO SCENE"
    %if game.active == s.id:
        %css  = "active"
        %hint = "ACTIVE SCENE"
    %end
    <div>
        <img class="{{css}}" src="{{url}}" onClick="activateScene({{s.id}})" draggable="false" title="{{hint}}" />
        <div class="controls">
            <img class="icon" src="/static/copy.png" onClick="cloneScene({{s.id}});" draggable="false" title="CLONE SCENE" />
            <img class="icon" src="/static/delete.png" onClick="deleteScene({{s.id}});" draggable="false" title="DELETE TOKEN" onMouseLeave="hideHint();" />
        </div>
    </div>
%end 
