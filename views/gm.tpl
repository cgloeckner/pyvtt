%include("header", title="GM {0}".format(gm.name))

%if len(all_games) > 0:
<div class="horizdropdown" onClick="openGmDropdown();">
	<div id="gmdrop">
	%include("games")
	</div>
	<div class="gmhint">
		<img id="gmhint" src="/static/bottom.png" />
	</div>
</div>
%end

<div class="menu" ondragover="GmUploadDrag(event);" ondrop="GmUploadDrop(event, '{{!engine.url_regex.replace('\\', '\\\\')}}', '{{gm.url}}');" onClick="closeGmDropdown();">  

<hr />

<h1>GAMES by {{gm.name}}</h1>

	<div class="form">
		<p>ENTER GAME NAME (optional)</p>
		<p><input type="text" id="url" value="" maxlength="20" autocomplete="off" /></p>
		<p></p>
		
		<div class="dropzone" id="dropzone">                                           
			<p>DRAG AM IMAGE TO START</p>
			<form id="uploadform" method="post" enctype="multipart/form-data">
				<input id="uploadqueue" name="file" type="file" />
			</form>
		</div>      
		
		<br />  
	</div>
	
	<div id="error"></div>
<hr />

</div>

<script>
	$('#drophint').fadeIn(1000, 0.0);
</script>

%include("footer")
