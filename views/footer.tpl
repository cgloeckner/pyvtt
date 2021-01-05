%import requests, json
%import bottle

<span class="imprint">
%if engine.imprint is not None:
	<a href="{{!engine.imprint['url']}}" target="_blank">{{engine.imprint['label']}}</a>
%end
</span>

</div>
</body>

</html>
