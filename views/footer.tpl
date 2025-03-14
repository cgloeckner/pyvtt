%import requests
%import json
%import time
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
        %provider = engine.login_api.parse_provider(gm.metadata)
        %url = engine.login_api.get_icon_url(provider)
    %end
    <span title="{{provider.upper()}} via {{gm.identity.upper()}}" class="hint"><img src="{{url}}" class="icon_only" /> {{gm.name}}</span>
%end
</span>

<span class="links">

%maintenance = engine.maintenance.load()
%if maintenance > time.time():
    %include("maintenance", timestamp=maintenance)
%end

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
