%include("header", title=game.active)

<form action="/upload/{{game.title}}" method="post" enctype="multipart/form-data">
	<input name="file[]" type="file" multiple />
	<input type="submit" value="upload" />
</form>

<div class="scene">
	<canvas id="battlemap" width="1440" height="720"></canvas>
</div>

<div id="token">
	<span id="info"></span>
	<input type="checkbox" name="locked" id="locked" onChange="tokenLock()" />
	<label for="locked">Locked</label>
	<input type="button" onClick="tokenClone()" value="clone" />
	<input type="button" onClick="tokenDelete()" value="delete" />
</div>

<!--

<input type="button" onClick="start('{{game.title}}')" value="start" />
-->

<script>
var battlemap = $('#battlemap')[0]

/** Mobile controls not working yet
battlemap.addEventListener('touchstart', tokenClick);
battlemap.addEventListener('touchmove', tokenMove);
battlemap.addEventListener('touchend', tokenRelease);
*/

// desktop controls
battlemap.addEventListener('mousedown', tokenClick);
battlemap.addEventListener('mousemove', tokenMove);
battlemap.addEventListener('mouseup', tokenRelease);
battlemap.addEventListener('wheel', tokenWheel);

start('{{game.title}}');
</script>

%include("footer")

