<div id="login">
    <div class="menu">
        <hr />
        <h1>{{game.url.upper()}} by {{gm.name}}</h1>
        
        <img class="logo" src="/static/logo.png" />
        
        <div class="form">
            <form onsubmit="login(event, '{{gm.url}}', '{{game.url}}', '{{websocket_url}}');">
                <p>PLAYER NAME</p>
                <input type="text" name="playername" id="playername" autocomplete="off" value="{{playername}}" maxlength="30" />
                
                <p>PLAYER COLOR</p>
                <input type="color" name="playercolor" id="playercolor" value="{{playercolor}}"><img src="/static/rotate.png" class="icon" title="RANDOM COLOR" onClick="pickRandomColor();" />
                
                <p><input type="submit" id="loginbtn" value="JOIN" /></p>
            </form> 
        </div> 
        <hr />
    </div>  
</div>
