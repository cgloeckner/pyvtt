%include("header", title='Redirecting...')

<div class="menu">

<p>Welcome, {{playername}}. You'll be redirected to the <a href="/play/{{game.url}}">Game</a> in a second...</p>

<script type="text/javascript">
<!--
window.location = "/play/{{game.url}}";
//–>
</script>

</div>

%include("footer")

