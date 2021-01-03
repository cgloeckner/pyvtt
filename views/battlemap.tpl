%include("header", title=game.url.upper())
  
%include("login")

<div id="game">
%if is_gm:
	<div class="horizdropdown" onClick="openGmDropdown();">
		<div id="gmdrop">
	%include("scenes")
		</div>
		<img id="gmhint" src="/static/bottom.png" />
	</div>
%end

	<div class="verticdropdown" onClick="openSettingsDropdown()">
		<div id="settingsdrop">
			<div>
				<p><input type="checkbox" id="zooming" onChange="enableZooming();" /> <label for="zooming">Zoom</label></p>
			</div>
		</div>
		<img id="settingshint" src="/static/settings.png" />
	</div>

	<div id="dicebox">
		<div class="dice" id="dice">
%for d in [20, 12, 10, 8, 6, 4]:
			<img src="/static/d{{d}}.png" id="d{{d}}" title="Roll 1D{{d}}" draggable="false" onClick="rollDice({{d}});" />
%end
		</div>
		<div class="rollbox" id="rollbox">
%for d in [20, 12, 10, 8, 6, 4]:
			<div id="d{{d}}box"></div>
%end
		</div>
	</div>

	<div class="battlemap" id="gamecontent">
		<div id="draghint">DRAG AN IMAGE TO START</div>
		<canvas id="battlemap" width="1000" height="560"></canvas>
			
		<div id="tokenbar">
			<img src="/static/flipx.png" id="tokenFlipX" draggable="false" onClick="onFlipX();" />
			<img src="/static/locked.png" id="tokenLock" draggable="false" onClick="onLock();" />
			<img src="/static/top.png" id="tokenTop" draggable="false" onClick="onTop();" />
			<img src="/static/bottom.png" id="tokenBottom" draggable="false" onClick="onBottom();" />
			<img src="/static/resize.png" id="tokenResize" onDragStart="onResize();" onDragEnd="onQuitAction();"/>
			<img src="/static/rotate.png" id="tokenRotate" onDragStart="onRotate();" onDragEnd="onQuitAction();" />
		</div>
	</div>

	<div class="mapfooter" id="mapfooter">
		<div id="players"></div>

		<form id="uploadform" method="post" enctype="multipart/form-data">
			<input id="uploadqueue" name="file[]" type="file" multiple />
		</form>
	</div>
</div>

%include("footer")

