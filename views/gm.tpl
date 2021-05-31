%include("header", title="GM {0}".format(gm.name))

%if len(all_games) > 0:
<div class="horizdropdown" onClick="openGmDropdown();">
    <div id="gmdrop">
    %include("games")
    </div>
    <div class="gmhint">
        <img id="gmhint" src="/static/bottom.png" draggable="false" title="SHOW MY GAMES"  />
    </div>
</div>
%end

<div class="menu" ondragover="GmUploadDrag(event);" ondrop="GmUploadDrop(event, '{{!engine.url_regex.replace('\\', '\\\\')}}', '{{gm.url}}');" onClick="closeGmDropdown();">  

<hr />

<h1>GAMES by {{gm.name}}</h1>

    <div class="form">
        <p>ENTER GAME NAME (optional)</p>
        <p><input type="text" id="url" value="" maxlength="30" autocomplete="off" /> <img src="/static/rotate.png" class="icon" onClick="fancyUrl();" title="PICK RANDOM NAME" draggable="false" /></p>
        <p></p>
        
        <div class="dropzone" id="dropzone">                                           
            <p id="draghint"><span onClick="initUpload();">DRAG AN IMAGE AS BACKGROUND</span><span><br /><br /><span onClick="GmQuickStart('{{!engine.url_regex.replace('\\', '\\\\')}}');">OR CLICK TO START WITHOUT</span></p>
            <form id="uploadform" method="post" enctype="multipart/form-data">
                <input id="uploadqueue" name="file" type="file" />
            </form>
        </div>      
        
        <br />

        <!-- stays hidden -->
        <div id="uploadscreen">
            <form id="fileform" method="post" enctype="multipart/form-data">
                <input type="file" id="fileupload" name="file" accept="image/*" multiple onChange="mobileGmUpload('{{!engine.url_regex.replace('\\', '\\\\')}}', '{{gm.url}}');">
            </form>
        </div> 
    </div>
    
<hr />

</div>

<div id="popup"></div>
<div id="hint"></div>   

%include("footer")
