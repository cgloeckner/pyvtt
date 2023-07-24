    <div id="drawing">
        <div>
            <div>
                <input type="color" name="pencolor" id="pencolor" value="#000000" onChange="onPickColor()">
                <button id="upload" onClick="onUploadDrawing();">ADD TO SCENE</button>

                <span class="icons">
                    <img class="largeicon" id="cardmode" src="/static/card-icon.png" onClick="onToggleMode('card')"draggable="false" title="CREATE INDEX CARD" />
                    <img class="largeicon" id="overlaymode" src="/static/transparent-icon.png" onClick="onToggleMode('overlay')"draggable="false" title="CREATE OVERLAY" />
                    <img class="largeicon" id="tokenmode" src="/static/token-icon.png" onClick="onToggleMode('token')" draggable="false" title="CREATE TOKEN" />
                    <img class="largeicon" src="/static/export.png" onClick="onExportDrawing();" draggable="false" title="DOWNLOAD" />
                    <img class="largeicon" src="/static/close.png" onClick="onCloseDrawing();" draggable="false" title="DISCARD" />
                </span>
            </div>
            <br />
            <canvas id="doodle" width="1600" height="1200" onpointerdown="onMovePen(event)" onpointerup="onReleasePen(event)" onpointermove="onMovePen(event)" onwheel="onWheelPen(event)" onDrop="onDropTokenImage(event)"></canvas>

            <img class="largeicon" id="undo_button" src="/static/undo.png" title="UNDO" onClick="onUndo()" />
            <div class="centered" id="token_toolbox">
                ZOOM: <input type="range" id="token_scale" min="1" max="200" value="100" onInput="onChangeSize()" />
                <input type="checkbox" id="token_pop" checked="" onChange="onChangePop()" /><label for="token_pop">MAKE IT POP</label>
            </div>
        </div>
    </div>
