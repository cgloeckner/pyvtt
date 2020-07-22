%include("header", title=game.active)

<div class="scene">
	<div class="dice">
		<img src="/static/d4.png" onClick="rollDice(4);"><br />
		<img src="/static/d6.png" onClick="rollDice(6);"><br />
		<img src="/static/d8.png" onClick="rollDice(8);"><br />
		<img src="/static/d12.png" onClick="rollDice(12);"><br />
		<img src="/static/d20.png" onClick="rollDice(20);"><br />
	</div>

	<div style="float: left;">
		<canvas id="battlemap" width="1000" height="720"></canvas>
	</div>
	
	<div id="rolls"></span>
</div>

<div class="gm">
	<form action="/upload/{{game.title}}" method="post" enctype="multipart/form-data">
		<input name="file[]" type="file" multiple />
		<input type="submit" value="upload" />
	</form>

	<input type="button" onClick="clearRolls()" value="clearRollLog" />
	<span id="info"></span>
	<input type="checkbox" name="locked" id="locked" onChange="tokenLock()" /><label for="locked">Locked</label>
	<input type="button" onClick="tokenClone()" value="clone" />
	<input type="button" onClick="tokenDelete()" value="delete" />
</div>

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

