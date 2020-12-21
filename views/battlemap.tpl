%title = '{0}: {1} by {2}'.format(playername, game.url, game.admin.name)

%include("header", title=title)

%if is_gm:
	%include("scene_dropdown")
%end

<div id="rollbox">
</div>

<div class="battlemap">
	<canvas id="battlemap" width="1000" height="560"></canvas>
		
	<div id="tokenbar">
		<img src="/static/flipx.png" id="tokenFlipX" onClick="tokenFlipX();" />
		<img src="/static/locked.png" id="tokenLock" onClick="tokenLock();" />
		<img src="/static/top.png" id="tokenTop" onClick="tokenTop();" />
		<img src="/static/bottom.png" id="tokenBottom" onClick="tokenBottom();" />
%if is_gm:
		<img src="/static/stretch.png" id="tokenStretch" onClick="tokenStretch();" />
%else:
		<img src="" class="dummy" id="tokenStretch" />
%end
	</div>
</div>

<div class="mapfooter">
	<div class="dice">
%if game.d20:
		<img src="/static/d20.png" id="d20" title="Roll 1D20" onClick="rollDice(20);" />
%end
%if game.d12:
		<img src="/static/d12.png" id="d12" title="Roll 1D12" onClick="rollDice(12);" />
%end
%if game.d10:
		<img src="/static/d10.png" id="d10" title="Roll 1D10" onClick="rollDice(10);" />
%end
%if game.d8:
		<img src="/static/d8.png" id="d8" title="Roll 1D8" onClick="rollDice(8);" />
%end
%if game.d6:
		<img src="/static/d6.png" id="d6" title="Roll 1D6" onClick="rollDice(6);" />
%end
%if game.d4:
		<img src="/static/d4.png" id="d4" title="Roll 1D4" onClick="rollDice(4);" />
%end
	</div>					
					
	<div id="players"></div>

	<form id="uploadform" method="post" enctype="multipart/form-data">
		<input id="uploadqueue" name="file[]" type="file" multiple />
	</form>
</div>

<script>
// disable scrolling
//$('body').css('overflow', 'hidden');

var battlemap = $('#battlemap')[0];

$(window).on('unload', function() {
	disconnect();
});

// disable window context menu for token right click
document.addEventListener('contextmenu', event => {
  event.preventDefault();
});

// drop zone implementation (using canvas) --> also as players :) 
battlemap.addEventListener('dragover', uploadDrag);
battlemap.addEventListener('drop', uploadDrop);

// desktop controls
battlemap.addEventListener('mousedown', tokenGrab);
battlemap.addEventListener('mousemove', tokenMove);
battlemap.addEventListener('mouseup', tokenRelease);
battlemap.addEventListener('wheel', tokenWheel);
document.addEventListener('keydown', tokenShortcut);

// mobile control fix
battlemap.addEventListener('touchstart', tokenGrab);
battlemap.addEventListener('touchmove', tokenMove);
battlemap.addEventListener('touchend', tokenRelease);


start('{{game.url}}', '{{is_gm}}', '{{game.admin.name}}', '{{game.multiselect}}');
</script>

%include("footer")

