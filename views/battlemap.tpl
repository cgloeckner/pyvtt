%from orm import MAX_SCENE_WIDTH, MAX_SCENE_HEIGHT

%include("header", title=game.url.upper())
  
%include("login")

<div id="game" onDragOver="onDragStuff(event);">
%if is_gm:
	<div class="horizdropdown" onClick="openGmDropdown();">
		<div id="gmdrop">
	%include("scenes")
		</div>
		<div class="gmhint">
			<img id="gmhint" src="/static/bottom.png" draggable="false" />
		</div>
	</div>
%end

	<div class="verticdropdown" onClick="toggleHistoryDropdown()">
		<div id="historydrop"></div>
		<!--<img id="historyhint" src="/static/history.png" />//-->
	</div>
	
	<div id="dicehistory"></div>

	<div id="dicebox">
%for d in [20, 12, 10, 8, 6, 4, 2]:
		<img src="/static/d{{d}}.png" class="dice" id="d{{d}}icon" title="Roll 1D{{d}}" onMouseDown="onStartDragDice({{d}});" onMouseUp="onEndDragDice();" onDragEnd="onEndDragDice(event);" onClick="rollDice({{d}});" onMouseEnter="onEnterDice({{d}});" onMouseOut="onLeaveDice({{d}});" />
		<div class="rollbox" id="d{{d}}rolls"></div>
%end
	</div>

	<div class="battlemap" id="gamecontent">
		<div id="draghint">DRAG AN IMAGE AS BACKGROUND</div>
		<canvas id="battlemap" width="{{MAX_SCENE_WIDTH}}" height="{{MAX_SCENE_HEIGHT}}"></canvas>
			
		<div id="tokenbar">
			<img src="/static/flipx.png" id="tokenFlipX" draggable="false" onClick="onFlipX();" />
			<img src="/static/locked.png" id="tokenLock" draggable="false" onClick="onLock();" />
			<img src="/static/top.png" id="tokenTop" draggable="false" onClick="onTop();" />
			<img src="/static/bottom.png" id="tokenBottom" draggable="false" onClick="onBottom();" />
			<img src="/static/resize.png" id="tokenResize" onMouseDown="onResizeClick(event);" onDragStart="onStartResize();" onDragEnd="onQuitAction();"/>
			<img src="/static/rotate.png" id="tokenRotate" onMouseDown="onRotateClick(event);" onDragStart="onStartRotate();" onDragEnd="onQuitAction();" />
		</div>
	</div>

	<div id="players" onMouseDown="onStartDragPlayers(event);" onDragEnd="onEndDragPlayers();" onWheel="onWheelPlayers();"></div>
	
	<div class="mapfooter" id="mapfooter">
		<div id="ping">Ping: unknown</div>
		<div id="zoom" onClick="resetViewport();">Zoom: 100%</div>
		<div id="version">unknown version</div>
		<form id="uploadform" method="post" enctype="multipart/form-data">
			<input id="uploadqueue" name="file[]" type="file" multiple />
		</form>
	</div>
</div>

<div id="popup"></div> 

%include("footer")

