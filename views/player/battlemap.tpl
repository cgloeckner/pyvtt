%if gm:
	%title = '{0}@{1}'.format(game.title, game.active)
%else:
	%title = '{0} ({1})'.format(game.title, playername)
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
		<canvas id="battlemap" width="{{width}}" height="720"></canvas>
		
		<div>
			<div class="dicebox">
%for sides in [4, 6, 8, 10, 12, 20]:
				<img class="d{{sides}}" src="/static/d{{sides}}.png" onClick="rollDice({{sides}});" />
%end
			</div>
			<div id="players"></div>

%if gm:
			<form class="gmtools" action="/gm/{{game.title}}/upload" method="post" enctype="multipart/form-data">
				<input name="file[]" type="file" multiple />
				<input type="submit" value="upload" />
				<hr />
				<input type="checkbox" name="locked" id="locked" onChange="tokenLock()" /><label for="locked">Locked</label>
				<input type="button" onClick="tokenStretch()" value="stretch" />
				<input type="button" onClick="tokenBottom()" value="bottom" />
				<input type="button" onClick="tokenTop()" value="top" />
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

start('{{game.title}}', {{'true' if gm else 'false'}});
</script>

%include("footer")

