%from orm import MAX_SCENE_WIDTH, MAX_SCENE_HEIGHT

%include("header", title=game.url.upper())
   
<div id="popup"></div>
<div id="hint"></div> 

%include("login", timestamp=timestamp)

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
            <canvas id="snapshot" onClick="togglePreview(this);" title="CLICK TO ENLARGE"></canvas><br />
            <input type="button" id="applySnapshot" onClick="onApplyBackground();" value="APPLY BACKGROUND" />
        </span>
    </div>

    <!-- stays hidden -->
    <div id="uploadscreen">
        <form id="fileform" method="post" enctype="multipart/form-data">
            <input type="file" id="fileupload" name="file[]" accept="image/*, audio/*" multiple onChange="mobileUpload();">
        </form>
    </div>
%end

    <div id="drawing">
        <img class="close" src="/static/delete.png" onClick="closeDrawing();" draggable="false" title="DISCARD" />
        <span>
            <input type="color" name="pencolor" id="pencolor" value="#000000">
            <input type="range" name="penwidth" id="penwidth" min="1" max="100" step="1" value="20">
            <input type="checkbox" name="penenable" id="penenable"><label for="penenable">PEN</label>
            <button id="upload" onClick="onUploadDrawing();">UPLOAD</button>
              
            <canvas id="doodle" width="1600" height="900" onmousedown="onMovePen(event);" onmouseup="onReleasePen(event);" onmousemove="onMovePen(event);" ontouchstart="onMovePen(event);" ontouchmove="onMovePen(event);" ontouchend="onReleasePen(event);"></canvas>
        </span>
    </div>

    <div id="dicebox">
%for d in dice:
        <div class="dice" id="d{{d}}icon">
            <div>
                <img src="/static/d{{d}}.png" title="Roll 1D{{d}}" id="d{{d}}drag" onDragStart="onStartDragDice(event, {{d}});" onMouseDown="onResetDice(event, {{d}});" onDragEnd="onEndDragDice(event);" onClick="rollDice({{d}});" ontouchmove="onMobileDragDice(event, {{d}});" ontouchend="onEndDragDice(event);" />
                <div class="proofani" id="d{{d}}poofani"></div>
            </div>
        </div>
        <div class="rollbox" id="d{{d}}rolls"></div>
%end
    </div>

    <div class="battlemap" id="gamecontent">
        <div id="draghint"><span onClick="initUpload();">DRAG AN IMAGE AS BACKGROUND</span><br /><br /><span onClick="ignoreBackground();">OR CLICK TO SKIP</span></div>
        <canvas id="battlemap" width="{{MAX_SCENE_WIDTH}}" height="{{MAX_SCENE_HEIGHT}}"></canvas>
            
        <div id="tokenbar">
            <img src="/static/flipx.png" id="tokenFlipX" draggable="false" onClick="onFlipX();" ontouchstart="onFlipX();" title="HORIZONTAL FLIP" />
            <img src="/static/locked.png" id="tokenLock" draggable="false" onClick="onLock();" ontouchstart="onLock();" title="LOCK/UNLOCK" />
            <img src="/static/top.png" id="tokenTop" draggable="false" onClick="onTop();" ontouchstart="onTop();" title="MOVE TO TOP" />
            <img src="/static/copy.png" id="tokenClone" draggable="false" onClick="onClone();" ontouchstart="onClone();" title="CLONE TOKEN" />
            <img src="/static/delete.png" id="tokenDelete" draggable="false" onClick="onTokenDelete();" ontouchstart="onTokenDelete();" title="DELETE TOKEN" />
            <img src="/static/bottom.png" id="tokenBottom" draggable="false" onClick="onBottom();" ontouchstart="onBottom();" title="MOVE TO BOTTOM" />
            <img src="/static/louder.png" id="tokenLabelInc" draggable="false" onClick="onLabelStep(1);" ontouchstart="onLabelStep(1);" title="INCREASE NUMBER" />
            <img src="/static/label.png" id="tokenLabel" draggable="false" onClick="onLabel();" ontouchstart="onLabel();" title="ENTER LABEL" />
            <img src="/static/quieter.png" id="tokenLabelDec" draggable="false" onClick="onLabelStep(-1);" ontouchstart="onLabelStep(-1);" title="DECREASE LABEL" />
            <img src="/static/resize.png" id="tokenResize" onDragStart="onStartResize();" onDragEnd="onQuitAction(event);" ontouchmove="onTokenResize(event);" ontouchend="onQuitResize(event);" title="DRAG TO RESIZE" onClick="showTip('DRAG TO RESIZE');" />
            <img src="/static/rotate.png" id="tokenRotate" onDragStart="onStartRotate();" onDragEnd="onQuitAction(event);" ontouchmove="onTokenRotate(event);" ontouchend="onQuitRotate(event);" title="DRAG TO ROTATE" onClick="showTip('DRAG TO ROTATE');" />
        </div>
    </div>

    <div id="players" onDragStart="onStartDragPlayers(event);" onMouseDown="onResetPlayers(event);" onDragEnd="onEndDragPlayers(event);" onWheel="onWheelPlayers();" ontouchmove="onDragPlayers(event);"></div>
    
    <div class="audioplayer" draggable="false" id="musiccontrols">
        <audio id="audioplayer" loop></audio>
        <img src="/static/louder.png" draggable="false" onClick="onStepMusic(1);" title="MAKE LOUDER" />
        <div id="musicvolume"><img src="/static/muted.png" class="icon" /></div>
        <img src="/static/quieter.png" draggable="false" onClick="onStepMusic(-1);" title="MAKE QUIETER" />
        <div id="musicslots"></div>
    </div>

    <div id="playertools">
        <img class="largeicon" src="/static/pen.png" onClick="initDrawing(false);" draggable="false" title="DRAW INDEX CARD" /><br />
    </div>
    
    <div class="mapfooter" id="mapfooter">
        <div id="ping">Ping: &infin;</div>
        <div id="fps">0 FPS</div>
        <div id="version">unknown version</div>  
        <div id="assetsDownloading"></div>
        <div id="assetsUploading"></div>
        <div id="zoom">
            <!-- <img id="beamLock" class="icon" title="AUTO-MOVEMENT" onClick="onToggleAutoMove(event);" src="/static/unlocked.png" /> -->
            <span id="zoomLevel" title="RESET ZOOM" onClick="resetViewport();"></span>
        </div>

        <form id="uploadform" method="post" enctype="multipart/form-data">
            <input id="uploadqueue" name="file[]" type="file" multiple />
        </form>
    </div>

    <!-- <div id="debuglog" style="position: absolute; z-index: 100; width: 150px; height: 400px; right: 0px; background-color: white; overflow-y: scroll">-->
    </div>
</div>

%include("footer")

