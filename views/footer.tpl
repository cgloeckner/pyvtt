%import requests, json
%import bottle

%try:
    %gm
%except NameError:
    %gm = None
%end

<span id="auth">
%if gm is not None:
    GM <a href="/vtt/logout" draggable="false" title="CLICK TO LOGOUT">{{gm.name}}</a> <span>{{gm.identity}} ({{gm.metadata}})</span>
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
