%include("header", title='Redirecting...')

<div class="menu">

<p style="text-transform: uppercase;">Welcome, {{playername}}. You'll be redirected to the <a href="/{{game.admin.url}}/{{game.url}}">Game</a> in a second...</p>

<script type="text/javascript">
<!--
window.location = "/{{game.admin.url}}/{{game.url}}";
//–>
</script>

</div>

%include("footer")

