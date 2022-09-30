%import time
    <div class="tools">
        <img class="largeicon" src="{{engine.adjustStaticsUrl('/static/add.png')}}" onClick="addScene();" draggable="false" title="CREATE SCENE" />
        <img class="largeicon" src="{{engine.adjustStaticsUrl('/static/upload.png')}}" onClick="initUpload();" draggable="false" title="FILE UPLOAD" />
        <img class="largeicon" src="{{engine.adjustStaticsUrl('/static/pen.png')}}" onClick="initDrawing(true);" draggable="false" title="DRAW BACKGROUND" /><br />
        <img class="largeicon" src="{{engine.adjustStaticsUrl('/static/camera.png')}}" onClick="initWebcam();" draggable="false" title="PREVIEW WEBCAM" />
        <img class="largeicon" src="{{engine.adjustStaticsUrl('/static/screen.png')}}" onClick="initScreenShare();" draggable="false" title="PREVIEW SCREENSHARE" />
    </div>
    
%for i, scene_id in enumerate(game.order):
    %for s in game.scenes:
        %if scene_id == s.id:
            %if s.backing is None:   
                %url = {{engine.adjustStaticsUrl('/static/transparent.png')}}
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
            <img class="icon" src="{{engine.adjustStaticsUrl('/static/left.png')}}" onClick="moveScene({{s.id}}, -1);" draggable="false" title="MOVE LEFT" />
            %end
            <img class="icon" src="{{engine.adjustStaticsUrl('/static/copy.png')}}" onClick="cloneScene({{s.id}});" draggable="false" title="CLONE SCENE" />
            <img class="icon" src="{{engine.adjustStaticsUrl('/static/delete.png')}}" onClick="deleteScene({{s.id}});" draggable="false" title="DELETE SCENE" onMouseLeave="hideHint();" />
            %if i < len(game.order) - 1:
            <img class="icon" src="{{engine.adjustStaticsUrl('/static/right.png')}}" onClick="moveScene({{s.id}}, 1);" draggable="false" title="MOVE RIGHT" />
            %end
        </div>
    </div> 
        %end
    %end
%end
