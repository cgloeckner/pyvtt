%import requests, json
%import bottle

%try:
    %gm
%except NameError:
    %gm = None
%end

<span id="auth">
%if gm is not None:
    %provider = ''
    %url = ''
    %if engine.login_api is not None:
        %provider = engine.login_api.parseProvider(gm.metadata)
        %url = engine.login_api.getIconUrl(provider)
    %end
    GM <a href="/vtt/logout" draggable="false" title="CLICK TO LOGOUT">{{gm.name}} <img src="{{url}}" class="icon" title="{{provider}}" /></a>
    <span>{{gm.identity}}</span>
%end
</span>

<span class="links">
%if gm is not None:
    <a href="/vtt/logout" draggable="false">LOGOUT</a>
%end
%for data in engine.links:
    <a href="{{!data['url']}}" target="_blank" draggable="false">{{data['label']}}</a>
%end
</span>

</div>
</body>

</html>
