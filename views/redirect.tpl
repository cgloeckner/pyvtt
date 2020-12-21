%include("header", title='Redirecting...')

<div class="menu">

<p>Welcome, {{playername}}. You'll be redirected to the <a href="/{{game.admin.name}}/{{game.url}}">Game</a> in a second...</p>

<script type="text/javascript">
<!--
window.location = "/{{game.admin.name}}/{{game.url}}";
//–>
</script>

</div>

%include("footer")

