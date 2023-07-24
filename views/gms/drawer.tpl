%if len(all_games) > 0:
<div class="horizdropdown" onClick="openGmDropdown();">
    <div id="gmdrop">
    %include("gms/games")
    </div>
    <div class="gmhint">
        <img id="gmhint" src="/static/bottom.png" draggable="false" title="SHOW MY GAMES"  />
    </div>
</div>
%end
