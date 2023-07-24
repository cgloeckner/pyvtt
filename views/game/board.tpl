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
