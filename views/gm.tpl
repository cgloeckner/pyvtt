%import calendar, datetime
%include("header", title="GM {0}".format(gm.name))

%include("gms/drawer")

<img class="largeicon schedule" id="schedule_icon" src="/static/clock.png" onClick="showSchedule();" draggable="false" title="SCHEDULE" /> 

<div class="menu" ondragover="GmUploadDrag(event);" ondrop="GmUploadDrop(event, '{{!engine.url_regex.replace('\\', '\\\\')}}', '{{gm.url}}');" onClick="closeGmDropdown()">  

    %include("gms/scheduler")

    <hr />

    %include("gms/creator")

    <hr />

</div>

<div id="popup"></div>
<div id="hint"></div>   

%include("footer", gm=gm)

