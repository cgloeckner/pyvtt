%from orm import MAX_SCENE_WIDTH, MAX_SCENE_HEIGHT

%you_are_host = gm is not None and gm.url == host.url

%include("header", title=game.url.upper())
   
<div id="popup"></div>
<div id="hint"></div> 

%include("login", timestamp=timestamp, you_are_host=you_are_host)

<div id="game">
%if you_are_host:
    %include("gm_drawer")
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

    %include("game_drawing")

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

    %include("game_board")

    <div id="players" onDragStart="onStartDragPlayers(event);" onMouseDown="onResetPlayers(event);" onDragEnd="onEndDragPlayers(event);" onWheel="onWheelPlayers();" ontouchmove="onDragPlayers(event);"></div>
    
    <div class="audioplayer" draggable="false" id="musiccontrols">
%for n in range(engine.file_limit['num_music']):
        <audio id="audioplayer{{n}}" loop></audio>
%end
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
    </div>
</div>

%include("footer", gm=gm)

