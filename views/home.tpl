%include("header", title="GM: {0}".format(gm.name))

<div class="menu">

<h1>Games by {{gm.name}}</h1>

	<div id="preview">
%for g in gm.games.order_by(lambda g: g.id):
	%s = dbScene.select(lambda s: s.id == g.active).first()
	%url = "/static/empty.jpg"
	%if s.backing is not None:
		%url = s.backing.url
	%end
		<div>
			<p>
				<a href="/vtt/export-game/{{g.url}}"><img class="icon" src="/static/export.png"></a>
				{{g.url}}
				<a href="/vtt/delete-game/{{g.url}}"><img class="icon" src="/static/delete.png" /></a>
			</p>
				<a href="/{{g.admin.name}}/{{g.url}}" target="_blank"><img class="thumbnail" src="{{url}}" /></a><br />
			Public Link: <a href="http://{{server}}/{{g.admin.name}}/{{g.url}}" target="_blank">here</a><br />
			
			<input type="checkbox" name="d4"  id="d4"  {{'checked="checked"' if g.d4 else ''}} onChange="toggleRule('{{gm.name}}', '{{g.url}}', 'd4');" />   <label for="d4" >D4</label>
			<input type="checkbox" name="d6"  id="d6"  {{'checked="checked"' if g.d6 else ''}} onChange="toggleRule('{{gm.name}}', '{{g.url}}', 'd6');" />   <label for="d6" >D6</label>
			<input type="checkbox" name="d8"  id="d8"  {{'checked="checked"' if g.d8 else ''}} onChange="toggleRule('{{gm.name}}', '{{g.url}}', 'd8');" />   <label for="d8" >D8</label>
			<input type="checkbox" name="d10" id="d10" {{'checked="checked"' if g.d10 else ''}} onChange="toggleRule('{{gm.name}}', '{{g.url}}', 'd10');" /> <label for="d10">D10</label>
			<input type="checkbox" name="d12" id="d12" {{'checked="checked"' if g.d12 else ''}} onChange="toggleRule('{{gm.name}}', '{{g.url}}', 'd12');" /> <label for="d12">D12</label>
			<input type="checkbox" name="d20" id="d20" {{'checked="checked"' if g.d20 else ''}} onChange="toggleRule('{{gm.name}}', '{{g.url}}', 'd20');" /> <label for="d20">D20</label><br />
			
			<input type="checkbox" name="multiselect" id="multiselect" {{'checked="checked"' if g.multiselect else ''}} onChange="toggleRule('{{gm.name}}', '{{g.url}}', 'multiselect');" /> <label for="multiselect">multiselect</label>
		</div>
%end
	</div>

	<br />

	<form action="/vtt/create-game" id="create_game" method="post" enctype="multipart/form-data">
		http://{{server}}/{{gm.name}}/<input type="text" name="game_url" value="my-game" /><input type="submit" value="Create" /><br />
		Game Import: <input type="file" name="archive" />
	</form>

	<br />
</div>

%include("footer")
