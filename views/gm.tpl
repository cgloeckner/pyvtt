%import calendar, datetime
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

%today = datetime.date.today()
%now = datetime.datetime.now().time()
%number_formatter = lambda n: '0{0}'.format(n) if n < 10 else n
<div id="schedule">
    <h1>SCHEDULE GAME</h1>
    <form>
        <p>DATE:
            <select id="day">
%max_days = calendar.monthrange(today.year, today.month)[1]
%for value in range(max_days):
    %selected = ' selected' if today.day == value+1 else ''
                <option value="{{value+1}}"{{selected}}>{{number_formatter(value+1)}}</option>
%end
            </select>
            <select id="month" onChange="updateDays();">
%for value in range(12):
    %selected = ' selected' if today.month == value+1 else ''
                <option value="{{value+1}}"{{selected}}>{{calendar.month_name[value+1].upper()}}</option>
%end
            </select>
            <input type="number" id="year" value="{{today.year}}" onChange="updateDays();" />
        </p>

        <p>TIME:
            <select id="hour">
%for hour in range(24): 
    %selected = ' selected' if now.hour == hour else ''
                <option value="{{hour}}"{{selected}}>{{number_formatter(hour)}}</option>
%end
            </select> :
            <select id="minute">
%for minute in range(60):   
    %selected = ' selected' if now.minute == minute else ''
                <option value="{{minute}}"{{selected}}>{{number_formatter(minute)}}</option>
%end
            </select>
        </p>

        <input type="hidden" id="schedule_base_url" value="" />
        <input type="button" onClick="createCountdown();" value="START COUNTDOWN" />
    </form>
</div>

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
