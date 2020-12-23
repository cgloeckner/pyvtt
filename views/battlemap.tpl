%title = '{0}: {1} by {2}'.format(playername, game.url.upper(), game.admin.name)

%include("header", title=title)
		   
%include("login")

<div id="game">
%if is_gm:
	<div class="dropdown" onClick="openDropdown();">
		<div id="preview">
	%include("dropdown")
		</div>
	</div>
%end

	<div id="rollbox">
	</div>

	<div class="battlemap">
		<div id="drag_hint">DRAG AN IMAGE TO START</div>
		<canvas id="battlemap" width="1000" height="560"></canvas>
			
		<div id="tokenbar">
			<img src="/static/flipx.png" id="tokenFlipX" draggable="false" onClick="tokenFlipX();" />
			<img src="/static/locked.png" id="tokenLock" draggable="false" onClick="tokenLock();" />
			<img src="/static/top.png" id="tokenTop" draggable="false" onClick="tokenTop();" />
			<img src="/static/bottom.png" id="tokenBottom" draggable="false" onClick="tokenBottom();" />
			<img src="/static/resize.png" id="tokenResize" onDragStart="tokenResize();" onDragEnd="tokenQuitAction();"/>
			<img src="/static/rotate.png" id="tokenRotate" onDragStart="tokenRotate();" onDragEnd="tokenQuitAction();" />
		</div>
	</div>

	<div class="mapfooter" id="mapfooter">
		<div class="dice">
%for d in [20, 12, 10, 8, 6, 4]:
			<img src="/static/d{{d}}.png" id="d{{d}}" title="Roll 1D{{d}}" draggable="false" onClick="rollDice({{d}});" />
%end
		</div>					
						
		<div id="players"></div>

		<form id="uploadform" method="post" enctype="multipart/form-data">
			<input id="uploadqueue" name="file[]" type="file" multiple />
		</form>
	</div>
</div>

%include("footer")

