%include("header", title=game.active)

<form action="/upload/{{game.title}}" method="post" enctype="multipart/form-data">
	<input name="file[]" type="file" multiple />
	<input type="submit" value="upload" />
</form>

<div class="scene">
	<canvas id="battlemap" width="1440" height="720" onMouseDown="tokenClick()" onMouseMove="tokenMove()" onMouseUp="tokenRelease()"></canvas>
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
battlemap.addEventListener('wheel', tokenWheel);
start('{{game.title}}');
</script>

%include("footer")

