%from orm import MAX_SCENE_WIDTH, MAX_SCENE_HEIGHT

%you_are_host = gm is not None and gm.url == host.url

%include("header", title=game.url.upper())
   
<div id="popup"></div>
<div id="hint"></div> 

%include("login", timestamp=timestamp, you_are_host=you_are_host)

<div id="game">
%if you_are_host:
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

    <div id="assetsbrowser">
        <img class="browse" src="/static/upload.png" onClick="initUpload();" draggable="false" title="FILE UPLOAD" />
        <img class="close" src="/static/delete.png" onClick="hideAssetsBrowser();" draggable="false" title="DISCARD" />
        <select id="games" onChange="loadAssets()">
            <option value="null">{{engine.title}} Assets</option>
        </select>
        <div id="assets"></div>
    </div>
%end

    <!-- stays hidden -->
    <div id="uploadscreen">
        <form id="fileform" method="post" enctype="multipart/form-data">
            <input type="file" id="fileupload" name="file[]" accept="image/*, audio/*" multiple onChange="browseUpload();">
        </form>

        <form id="fileform" method="post" enctype="multipart/form-data">
            <input type="file" id="tokenupload" name="file" accept="image/*" onChange="onPrepareToken();">
        </form>
    </div>

    <div id="drawing">
        <div>
            <div>
                <input type="color" name="pencolor" id="pencolor" value="#000000" onChange="onPickColor()">
                <button id="upload" onClick="onUploadDrawing();">UPLOAD</button>

                <span class="icons">
                    <img class="largeicon" id="cardmode" src="/static/card-icon.png" onClick="onToggleMode('card')"draggable="false" title="CREATE INDEX CARD" />
                    <img class="largeicon" id="overlaymode" src="/static/transparent-icon.png" onClick="onToggleMode('overlay')"draggable="false" title="CREATE OVERLAY" />
                    <img class="largeicon" id="tokenmode" src="/static/token-icon.png" onClick="onToggleMode('token')" draggable="false" title="CREATE TOKEN" />
                    <img class="largeicon" src="/static/export.png" onClick="onExportDrawing();" draggable="false" title="DOWNLOAD" />
                    <img class="largeicon" src="/static/delete.png" onClick="onCloseDrawing();" draggable="false" title="DISCARD" />
                </span>
            </div>
            <br />
            <canvas id="doodle" width="1600" height="1200" onmousedown="onMovePen(event)" onmouseup="onReleasePen(event)" onmousemove="onMovePen(event)" onwheel="onWheelPen(event)" ontouchstart="onMovePen(event)" ontouchmove="onMovePen(event)" ontouchend="onReleasePen(event)" onDrop="onDropTokenImage(event)"></canvas>

            <img class="largeicon" id="undo_button" src="/static/undo.png" title="UNDO" onClick="onUndo()" />
            <div class="centered">
                <input type="range" id="token_scale" min="1" max="200" value="100" onInput="onChangeSize()" />
            </div>
        </div>
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

    <div id="rollhistory" onClick="toggleRollHistory();"></div>

    <!-- <div id="debuglog" style="position: absolute; z-index: 100; width: 150px; height: 400px; left: 0px; background-color: white; overflow-y: scroll"> -->
    </div>
</div>

%include("footer", gm=gm)

