%include("header", title="COUNTDOWN")

<div id="login">
    <div class="menu">
        <hr />
        <h1>GAME COUNTDOWN</h1>
        
        <img class="logo" src="/static/logo.png" />
        <div id="countdown"></div>
    </div>
</div>

<script>
onCountdown('{{timestamp}}', 'COUNTDOWN EXPIRED');
</script>

%include("footer")
