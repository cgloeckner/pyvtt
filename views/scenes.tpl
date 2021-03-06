    <img class="largeicon" src="/static/add.png" onClick="addScene();" draggable="false" onMouseEnter="showHint(event, 'CREATE SCENE');" onMouseLeave="hideHint();" />
%for s in game.scenes.order_by(lambda s: s.id):
    %url = "/static/empty.jpg"
    %if s.backing is not None:
        %url = s.backing.url
    %end
    %css = "thumbnail"
    %if game.active == s.id:
        %css = "active"
    %end
    <div>
        <img class="{{css}}" src="{{url}}" onClick="activateScene({{s.id}})" draggable="false" onMouseEnter="showHint(event, 'SWITCH TO SCENE');" onMouseLeave="hideHint();" />
        <div class="controls">
            <img class="icon" src="/static/copy.png" onClick="cloneScene({{s.id}});" draggable="false" onMouseEnter="showHint(event, 'CLONE SCENE');" onMouseLeave="hideHint();" />
            <img class="icon" src="/static/delete.png" onClick="deleteScene({{s.id}});" draggable="false" onMouseEnter="showHint(event, 'DELETE TOKEN');" onMouseLeave="hideHint();" />
        </div>
    </div>
%end 
