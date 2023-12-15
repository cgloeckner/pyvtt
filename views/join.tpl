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
%else:
    %for provider in engine.login_api.providers:
        <p><a href="{{engine.login_api.providers[provider].getAuthUrl()}}"><input type="button" class="login_button" value="LOGIN WITH {{provider.upper()}}" /></a></p>
    %end
%end  
    </form>  
</div>

Are you a player? Ask your GM for the game link.

<hr />

</div>

<div id="popup"></div> 

%include("footer")

