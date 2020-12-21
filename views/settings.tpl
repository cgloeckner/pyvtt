%include("header", title="GM: {0}".format(gm.name))

<div class="menu">

<h1>SETTINGS for {{game.url.upper()}}</h1>

<form action="/vtt/modify-game/{{game.url}}" id="modify_game" method="post" enctype="multipart/form-data">

	<input type="checkbox" name="d4"  id="d4"  {{'checked="checked"' if game.d4 else ''}} />  
	<label for="d4">D4</label><br />

	<input type="checkbox" name="d6"  id="d6"  {{'checked="checked"' if game.d6 else ''}} />  
	<label for="d6">D6</label><br />

	<input type="checkbox" name="d8"  id="d8"  {{'checked="checked"' if game.d8 else ''}} />  
	<label for="d8">D8</label><br />

	<input type="checkbox" name="d10" id="d10" {{'checked="checked"' if game.d10 else ''}} /> 
	<label for="d10">D10</label><br />

	<input type="checkbox" name="d12" id="d12" {{'checked="checked"' if game.d12 else ''}} /> 
	<label for="d12">D12</label><br />

	<input type="checkbox" name="d20" id="d20" {{'checked="checked"' if game.d20 else ''}} /> 
	<label for="d20">D20</label><br />
	
	<input type="checkbox" name="multiselect" id="multiselect" {{'checked="checked"' if game.multiselect else ''}} />
	<label for="multiselect">MULTISELECT</label><br />

	<input type="submit" value="SAVE" /><br />

</form>

</div>

%include("footer")
