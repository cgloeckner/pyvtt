%include("header", title=game.active)

<p>Welcome, {{playername}}. You'll be redirected to the <a href="/play/{{game.title}}">Game</a> in a second...</p>

<script type="text/javascript">
<!--
window.location = "/play/{{game.title}}";
//–>
</script>

%include("footer")

