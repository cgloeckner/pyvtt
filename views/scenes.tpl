%import time
    <div class="tools">
        <img class="largeicon" src="/static/add.png" onClick="addScene();" draggable="false" title="CREATE SCENE" />
        <img class="largeicon" src="/static/upload.png" onClick="initUpload();" draggable="false" title="FILE UPLOAD" /><br />
        <img class="largeicon" src="/static/camera.png" onClick="initWebcam();" draggable="false" title="PREVIEW WEBCAM" />
        <img class="largeicon" src="/static/screen.png" onClick="initScreenShare();" draggable="false" title="PREVIEW SCREENSHARE" />
    </div>
    
%for i, scene_id in enumerate(game.order):
    %for s in game.scenes:
        %if scene_id == s.id:
            %if s.backing is None:   
                %url = "/static/transparent.png"
            %else:
                %url = "/thumbnail/" + '/'.join([game.gm_url, game.url, str(s.id)])
            %end
            %css  = "thumbnail"
            %hint = "SWITCH TO SCENE"
            %if game.active == s.id:
                %css  = "active"
                %hint = "ACTIVE SCENE"
            %end
    <div class="element">
        <img class="{{css}}" src="{{url}}" onClick="activateScene({{s.id}})" draggable="false" title="{{hint}}" />
        <div class="controls">
            %if i > 0:
            <img class="icon" src="/static/left.png" onClick="moveScene({{s.id}}, -1);" draggable="false" title="MOVE LEFT" />
            %end
            <img class="icon" src="/static/copy.png" onClick="cloneScene({{s.id}});" draggable="false" title="CLONE SCENE" />
            <img class="icon" src="/static/delete.png" onClick="deleteScene({{s.id}});" draggable="false" title="DELETE SCENE" onMouseLeave="hideHint();" />
            %if i < len(game.order) - 1:
            <img class="icon" src="/static/right.png" onClick="moveScene({{s.id}}, 1);" draggable="false" title="MOVE RIGHT" />
            %end
        </div>
    </div> 
        %end
    %end
%end
