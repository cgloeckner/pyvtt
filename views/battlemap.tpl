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
            <img id="gmhint" src="/static/bottom.png" draggable="false" title="SHOW SCENES" />
        </div>
    </div>

    <div id="camerapreview">
        <img class="close" src="/static/delete.png" onClick="closeWebcam();" draggable="false" title="CLOSE CAMERA" />
        <span>
            <p>LIVESTREAM</p>
            <video id="video" playsinline autoplay onClick="togglePreview(this);" title="CLICK TO ENLARGE"></video><br />
            <input type="button" id="snapshotWebcam" onClick="onTakeSnapshot();" value="TAKE SNAPSHOT" />
        </span>

        <span>  
            <p>SNAPSHOT</p>
            <canvas id="snapshot" width="1600" height="900" onClick="togglePreview(this);" title="CLICK TO ENLARGE"></canvas><br />
            <input type="button" id="applySnapshot" onClick="onApplyBackground();" value="APPLY BACKGROUND" />
        </span>
    </div>
%end

    <div id="dicebox">
%for d in [20, 12, 10, 8, 6, 4, 2]:
        <div class="dice" id="d{{d}}icon">
            <div>
                <img src="/static/d{{d}}.png" title="Roll 1D{{d}}" id="d{{d}}drag" onDragStart="onStartDragDice(event, {{d}});" onMouseDown="onResetDice(event, {{d}});" onDragEnd="onEndDragDice(event);" onClick="rollDice({{d}});"ontouchmove="onMobileDragDice(event, {{d}});" />
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
            <img src="/static/flipx.png" id="tokenFlipX" draggable="false" onClick="onFlipX();" title="HORIZONTAL FLIP" />
            <img src="/static/locked.png" id="tokenLock" draggable="false" onClick="onLock();" title="LOCK/UNLOCK" />
            <img src="/static/top.png" id="tokenTop" draggable="false" onClick="onTop();" title="MOVE TO TOP" />
            <img src="/static/copy.png" id="tokenClone" draggable="false" onClick="onClone();" title="CLONE TOKEN" />
            <img src="/static/delete.png" id="tokenDelete" draggable="false" onClick="onTokenDelete();" title="DELETE TOKEN" />
            <img src="/static/bottom.png" id="tokenBottom" draggable="false" onClick="onBottom();" title="MOVE TO BOTTOM" />
            <img src="/static/louder.png" id="tokenLabelInc" draggable="false" onClick="onLabelStep(1);" title="INCREASE NUMBER" />
            <img src="/static/label.png" id="tokenLabel" draggable="false" onClick="onLabel();" title="ENTER LABEL" />
            <img src="/static/quieter.png" id="tokenLabelDec" draggable="false" onClick="onLabelStep(-1);" title="DECREASE LABEL" />
            <img src="/static/resize.png" id="tokenResize" onDragStart="onStartResize();" onDragEnd="onQuitAction(event);" ontouchmove="onTokenResize(event);" ontouchend="onQuitResize(event);" title="DRAG TO RESIZE" onClick="showTip('DRAG TO RESIZE');" />
            <img src="/static/rotate.png" id="tokenRotate" onDragStart="onStartRotate();" onDragEnd="onQuitAction(event);" ontouchmove="onTokenRotate(event);" ontouchend="onQuitRotate(event);" title="DRAG TO ROTATE" onClick="showTip('DRAG TO ROTATE');" />
        </div>
    </div>

    <div id="players" onDragStart="onStartDragPlayers(event);" onMouseDown="onResetPlayers(event);" onDragEnd="onEndDragPlayers(event);" onWheel="onWheelPlayers();" ontouchmove="onDragPlayers(event);"></div>
    
    <div class="audioplayer" draggable="true" id="musiccontrols" onDragStart="console.log('test'); onStartDragMusic(event);" onMouseDown="onResetMusic(event);" onDragEnd="onEndDragMusic(event);" ontouchmove="onDragMusic(event);">
        <audio id="audioplayer" loop></audio>
        <img src="/static/louder.png" draggable="false" onClick="onLouderMusic();" title="MAKE LOUDER" />
        <img src="/static/muted.png" id="toggleMusic" draggable="false" onClick="onToggleMusic();" title="TOGGLE MUSIC" />
        <img src="/static/quieter.png" draggable="false" onClick="onQuieterMusic();" title="MAKE QUIETER" />
        <img src="/static/delete.png" draggable="false" onClick="onClearMusic();" title="CLEAR MUSIC" />
    </div>
        
    <div class="mapfooter" id="mapfooter">
        <div id="ping">Ping: &infin;</div>
        <div id="fps">0 FPS</div>
        <div id="version">unknown version</div>
        <div id="zoom">
            <img id="beamLock" class="icon" title="AUTO-MOVEMENT" onClick="toggleAutoMove();" src="/static/unlocked.png" />
            <span id="zoomLevel" title="RESET ZOOM" onClick="resetViewport();"></span>
        </div>
        <div id="musicStatus">Music muted</div>
        <div id="assetsLoading"></div>

        <form id="uploadform" method="post" enctype="multipart/form-data">
            <input id="uploadqueue" name="file[]" type="file" multiple />
        </form>
    </div>

    <!--<div id="debuglog" style="position: absolute; z-index: 100; width: 150px; height: 400px; right: 0px; background-color: white; overflow-y: scroll">-->
    </div>
</div>

%include("footer")

