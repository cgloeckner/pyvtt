%include("header", title='JOIN as GM')

<div class="menu">

<hr />

<h1>JOIN as GM</h1>

<img class="logo" src="/static/logo.png" />
 
<div class="form">
       <form onsubmit="registerGm(event);">
%if engine.login_api is None:
        <p>GM NAME</p>
        <input type="text" id="gmname" maxlength="20" autocomplete="off" />
        
        <p><input type="submit" value="CREATE GM ACCOUNT" /></p>
%elif engine.login_api.api == 'patreon':
        <p><a href="{{engine.login_api.getAuthUrl()}}"><input type="button" value="LOG IN WITH {{engine.login_api.api.upper()}}" /></a></p>
%else:
    %raise NotImplementedError()
%end  
    </form>  
</div>

Are you a player? Ask your GM for the game link.

<hr />

</div>

<div id="popup"></div> 

%include("footer")

