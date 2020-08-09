%if gm:
	%title = '[GM] {0} @ {1}'.format(game.title, game.active)
%else:
	%title = '[{0}] {1}'.format(playername, game.title)
%end

%include("header", title=title)

<div id="players"></div>

<div class="scene">
	<div class="dicebox">
%for sides in [4, 6, 8, 10, 12, 20]:
		<img class="d{{sides}}" src="/static/d{{sides}}.png" onClick="rollDice({{sides}});" />
%end
		<div id="rollbox">
		</div>
		
%if gm:
		<div class="gm_info">
			<input type="checkbox" name="locked" id="locked" onChange="tokenLock()" /><label for="locked">Locked</label>
			<input type="button" onClick="tokenStretch()" value="stretch" />
			<input type="button" onClick="tokenBottom()" value="bottom" />
			<input type="button" onClick="tokenTop()" value="top" />
		</div>
%else:
		<input type="checkbox" style="display: none" name="locked" id="locked" onChange="tokenLock()" />
%end
	</div>
	
%width = 1000
%if gm:
	%width += 200
%end
	<div class="battlemap">
		<canvas id="battlemap" width="{{width}}" height="720"></canvas>
	</div>
</div>

%if gm:
<form class="upload" action="/gm/{{game.title}}/upload" method="post" enctype="multipart/form-data">
	<input name="file[]" type="file" multiple />
	<input type="submit" value="upload" />
</form>
%end

<script>
var battlemap = $('#battlemap')[0];

$(window).on('unload', function() {
	alert('pre');
	disconnect();
	alert('post');
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

start('{{game.title}}', '{{game.active}}');
</script>

%include("footer")

