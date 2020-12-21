/// Event handle to toggle a game "rule"
function toggleRule(gm_name, game_url, rule_key) {
	$.post('/vtt/toggle-rule/' + gm_name + '/' + game_url + '/' + rule_key);
}

