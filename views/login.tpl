<div id="login">
    <div class="menu">
        <hr />
        <h1>{{game.url.upper()}}
%if not you_are_host:
by {{host.name}}
%end
</h1>
        
        <img class="logo" src="/static/logo.png" />
        <div id="countdown"></div>
        
        <div class="form">
            <form onsubmit="login(event, '{{host.url}}', '{{game.url}}', '{{websocket_url}}');">
%if you_are_host:
                <p>GM NAME</p>
%else:
                <p>PLAYER NAME</p>
%end
                <input type="text" name="playername" id="playername" autocomplete="off" value="{{playername}}" maxlength="30" />
                                  
%if you_are_host:
                <p>GM COLOR</p>
%else:
                <p>PLAYER COLOR</p>
%end
                <input type="color" name="playercolor" id="playercolor" value="{{playercolor}}"><img src="/static/rotate.png" class="icon" title="RANDOM COLOR" onClick="pickRandomColor();" />
                
                <p><input type="submit" id="loginbtn" value="JOIN" /></p>
            </form> 
        </div> 
        <hr />
    </div>  
</div>

<script>
%if timestamp is not None:
    onCountdown('{{timestamp}}', 'GO FOR IT');
%else:
    onCountdown('0');
%end
</script>
