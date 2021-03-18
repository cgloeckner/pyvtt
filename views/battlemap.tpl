%from orm import MAX_SCENE_WIDTH, MAX_SCENE_HEIGHT

%include("header", title=game.url.upper())
   
<div id="popup"></div>
<div id="hint"></div> 

%include("login")

<div id="game">
%if is_gm:
    <div class="horizdropdown" onClick="openGmDropdown();">
        <div id="gmdrop">
    %include("scenes")
        </div>
        <div class="gmhint">
            <img id="gmhint" src="/static/bottom.png" draggable="false" onMouseEnter="showHint(event, 'SHOW SCENES');" onMouseLeave="hideHint();" />
        </div>
    </div>
%end

    <div id="dicebox">
%for d in [20, 12, 10, 8, 6, 4, 2]:
        <div class="dice" id="d{{d}}icon">
            <div>
                <img src="/static/d{{d}}.png" title="Roll 1D{{d}}" onDragStart="onStartDragDice(event, {{d}});" onMouseDown="onResetDice(event, {{d}});" onDragEnd="onEndDragDice(event);" onClick="rollDice({{d}});" />
                <div class="proofani" id="d{{d}}poofani"></div>
            </div>
        </div>
        <div class="rollbox" id="d{{d}}rolls"></div>
%end
    </div>

    <div class="battlemap" id="gamecontent">
        <div id="draghint">DRAG AN IMAGE AS BACKGROUND<br /><br /><span onClick="ignoreBackground();">OR CLICK TO SKIP</span></div>
        <canvas id="battlemap" width="{{MAX_SCENE_WIDTH}}" height="{{MAX_SCENE_HEIGHT}}"></canvas>
            
        <div id="tokenbar">
            <img src="/static/flipx.png" id="tokenFlipX" draggable="false" onClick="onFlipX();" onMouseEnter="showHint(event, 'VERTICAL FLIP');" onMouseLeave="hideHint();" />
            <img src="/static/locked.png" id="tokenLock" draggable="false" onClick="onLock();" onMouseEnter="showHint(event, 'LOCK/UNLOCK');" onMouseLeave="hideHint();" />
            <img src="/static/top.png" id="tokenTop" draggable="false" onClick="onTop();" onMouseEnter="showHint(event, 'MOVE TO TOP');" onMouseLeave="hideHint();" />
            <img src="/static/copy.png" id="tokenClone" draggable="false" onClick="onClone();" onMouseEnter="showHint(event, 'CLONE TOKEN');" onMouseLeave="hideHint();" />
            <img src="/static/delete.png" id="tokenDelete" draggable="false" onClick="onTokenDelete();" onMouseEnter="showHint(event, 'DELETE TOKEN');" onMouseLeave="hideHint();" />
            <img src="/static/bottom.png" id="tokenBottom" draggable="false" onClick="onBottom();" onMouseEnter="showHint(event, 'MOVE TO BOTTOM');" onMouseLeave="hideHint();" />
            <img src="/static/resize.png" id="tokenResize" onMouseDown="onResizeReset(event);" onDragStart="onStartResize();" onDragEnd="onQuitAction(event);" onMouseEnter="showHint(event, 'DRAG TO RESIZE');" onMouseLeave="hideHint();" onClick="showTip('DRAG TO RESIZE');" />
            <img src="/static/rotate.png" id="tokenRotate" onMouseDown="onRotateReset(event);" onDragStart="onStartRotate();" onDragEnd="onQuitAction(event);" onMouseEnter="showHint(event, 'DRAG TO ROTATE');" onMouseLeave="hideHint();"  onClick="showTip('DRAG TO ROTATE');" />
        </div>
    </div>

    <div id="players" onDragStart="onStartDragPlayers(event);" onMouseDown="onResetPlayers(event);" onDragEnd="onEndDragPlayers(event);" onWheel="onWheelPlayers();"></div>
    
    <div class="mapfooter" id="mapfooter">
        <div id="ping">Ping: &infin;</div>
        <div id="fps">0 FPS</div>
        <div id="zoom" onClick="resetViewport();">Zoom: 100%</div>
        <div id="version">unknown version</div>
        <form id="uploadform" method="post" enctype="multipart/form-data">
            <input id="uploadqueue" name="file[]" type="file" multiple />
        </form>
    </div>
</div>

%include("footer")

