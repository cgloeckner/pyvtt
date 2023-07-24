<h1>GAMES by <a href="/vtt/logout" title="CLICK TO LOGOUT">{{gm.name}}</a></h1>

    <div class="form">
        <p>ENTER GAME NAME (optional)</p>
        <p><input type="text" id="url" value="" maxlength="30" autocomplete="off" /> <img src="/static/rotate.png" class="icon" onClick="fancyUrl();" title="PICK RANDOM NAME" draggable="false" /></p>
        <p></p>

        <div class="dropzone" id="dropzone">
            <p id="draghint">
                <span onClick="initUpload();">DRAG AN IMAGE AS BACKGROUND</span>
                <span>
                    <br /><br />
                    <span onClick="GmQuickStart('{{!engine.url_regex.replace('\\', '\\\\')}}');">OR CLICK TO START WITHOUT</span>
                </span>
            </p>
            <form id="uploadform" method="post" enctype="multipart/form-data">
                <input id="uploadqueue" name="file" type="file" />
            </form>
        </div>

        <br />

        <!-- stays hidden -->
        <div id="uploadscreen">
            <form id="fileform" method="post" enctype="multipart/form-data">
                <input type="file" id="fileupload" name="file" accept="image/*" multiple onChange="browseGmUpload('{{!engine.url_regex.replace('\\', '\\\\')}}', '{{gm.url}}');">
            </form>
        </div>
    </div>

<hr />
