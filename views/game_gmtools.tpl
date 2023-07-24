    <div class="horizdropdown" onClick="openGmDropdown();">
        <div id="gmdrop">
    %include("game_scenes")
        </div>
        <div class="gmhint">
            <img id="gmhint" src="/static/bottom.png" draggable="false" title="SHOW SCENES" />
        </div>
    </div>

    <div id="camerapreview">
        <img class="hide" src="/static/top.png" onClick="hideWebcam();" draggable="false" title="HIDE CAMERA" />
        <img class="close" src="/static/close.png" onClick="closeWebcam();" draggable="false" title="CLOSE CAMERA" />
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
        <img class="close" src="/static/close.png" onClick="hideAssetsBrowser();" draggable="false" title="DISCARD" />
        <select id="games" onChange="loadAssets()">
            <option value="null">{{engine.title}} Assets</option>
        </select>
        <div id="assets"></div>
    </div>