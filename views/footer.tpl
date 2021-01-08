%import requests, json
%import bottle

<span class="links">
%for data in engine.links:
	<a href="{{!data['url']}}" target="_blank">{{data['label']}}</a>
%end
</span>

</div>
</body>

</html>
