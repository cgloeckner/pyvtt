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
		<!--	<img src="/static/resize.png" id="tokenResize" draggable="false" onClick="tokenResize();" /> -->
		</div>
	</div>

	<div class="mapfooter" id="mapfooter">
		<div class="dice">
%if game.d20:
			<img src="/static/d20.png" id="d20" title="Roll 1D20" draggable="false" onClick="rollDice(20);" />
%end
%if game.d12:
			<img src="/static/d12.png" id="d12" title="Roll 1D12" draggable="false" onClick="rollDice(12);" />
%end
%if game.d10:
			<img src="/static/d10.png" id="d10" title="Roll 1D10" draggable="false" onClick="rollDice(10);" />
%end
%if game.d8:
			<img src="/static/d8.png" id="d8" title="Roll 1D8" draggable="false" onClick="rollDice(8);" />
%end
%if game.d6:
			<img src="/static/d6.png" id="d6" title="Roll 1D6" draggable="false" onClick="rollDice(6);" />
%end
%if game.d4:
			<img src="/static/d4.png" id="d4" title="Roll 1D4" draggable="false" onClick="rollDice(4);" />
%end
		</div>					
						
		<div id="players"></div>

		<form id="uploadform" method="post" enctype="multipart/form-data">
			<input id="uploadqueue" name="file[]" type="file" multiple />
		</form>
	</div>
</div>

%include("footer")

