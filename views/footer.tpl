%import requests, json
%import bottle

<span id="auth">
%try:
    %if gm is not None:
        GM <a href="/vtt/logout" draggable="false" title="CLICK TO LOGOUT">{{gm.name}}</a>
        %if engine.login_api is not None:
{{!engine.login_api.getGmInfo(gm.url)}}
        %end
    %end
%except NameError:
    %pass
%end
</span>

<span class="links">
%for data in engine.links:
    <a href="{{!data['url']}}" target="_blank" draggable="false">{{data['label']}}</a>
%end
</span>

</div>
</body>

</html>
