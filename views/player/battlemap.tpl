%if gm:
	%title = 'GM: {0}'.format(game.title)
%else:
	%title = '{0} (as {1})'.format(game.title, playername)
%end

%include("header", title=title)

<div class="scene">
	<div id="rollbox">
	</div>

%width = 1000
%if gm:
	%width += 200
%end
	<div class="battlemap">
		<div id="tokenmenu">
			<input type="checkbox" name="locked" id="locked" onChange="tokenLock()" /><label for="locked">Locked</label>
			<input type="button" onClick="tokenStretch()" value="stretch" />
			<input type="button" onClick="tokenBottom()" value="bottom" />
			<input type="button" onClick="tokenTop()" value="top" />
		</div>
		<canvas id="battlemap" width="{{width}}" height="720"></canvas>
		
		<div>
			<div class="dicebox">
%for sides in [4, 6, 8, 10, 12, 20]:
				<img src="/static/d{{sides}}.png" onClick="rollDice({{sides}});" title="Roll 1D{{sides}}" />
%end
			</div>
			<div id="players"></div>

%if gm:
			<form id="uploadform" action="/gm/{{game.title}}/upload" method="post" enctype="multipart/form-data">
				<input id="uploadqueue" name="file[]" type="file" multiple />
				<input type="submit" value="upload" />
			</form>

%else:
			<input type="checkbox" style="display: none" name="locked" id="locked" onChange="tokenLock()" />
%end
		</div>
	</div>
	
	
</div>

<script>
var battlemap = $('#battlemap')[0];

$(window).on('unload', function() {
	disconnect();
});

/** Mobile controls not working yet
battlemap.addEventListener('touchstart', tokenGrab);
battlemap.addEventListener('touchmove', tokenMove);
battlemap.addEventListener('touchend', tokenRelease);
*/

// desktop controls
battlemap.addEventListener('mousedown', tokenGrab);
battlemap.addEventListener('mousemove', tokenMove);
battlemap.addEventListener('mouseup', tokenRelease);
battlemap.addEventListener('wheel', tokenWheel);
document.addEventListener('keydown', tokenShortcut);

// drop zone implementation (using canvas) --> also as players :) 
battlemap.addEventListener('dragover', uploadDrag);
battlemap.addEventListener('drop', uploadDrop);

// context menu implementing for token's
document.addEventListener('mousemove', mouseMove);
document.addEventListener('contextmenu', event => {
  event.preventDefault();
});

start('{{game.title}}', {{'true' if gm else 'false'}}, '{{playercolor}}');
</script>

%include("footer")

