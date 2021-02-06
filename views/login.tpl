<div id="login">

    <script>
    if(/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        showError('MOBILE DEVICES NOT SUPPORTED');
    }
    </script>
    
    <div class="menu">
        <hr />
        <h1>{{game.url.upper()}} by {{gm.name}}</h1>
        
        <img class="logo" src="/static/logo.png" />
        
        <div class="form">
            <form onsubmit="login(event, '{{gm.url}}', '{{game.url}}', '{{websocket_url}}');">
                <p>PLAYER NAME</p>
                <input type="text" name="playername" id="playername" autocomplete="off" value="{{playername}}" maxlength="30" />
                
                <p>PLAYER COLOR</p>
                <input type="color" name="playercolor" id="playercolor" value="{{playercolor}}">
                
                <p><input type="submit" id="loginbtn" value="JOIN" /></p>
            </form> 
        </div> 
        <hr />
    </div>  
</div>
