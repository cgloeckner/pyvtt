function openGmDropdown(force=false) {
	var scenes = $('#gmdrop');
	var hint   = $('#gmhint');
	if (force || !gm_dropdown) {
		scenes.animate({
			top: "+=122"
		}, 500);
		hint.animate({
			top: "+=122"
		}, 500);
	}
	gm_dropdown = true;
	hint.fadeOut(500, 0.0);
	
	closeSettingsDropdown(force);
}

function closeGmDropdown(force=false) { 
	var scenes = $('#gmdrop');
	var hint   = $('#gmhint');
	if (scenes != null) {
		if (force || gm_dropdown) {
			scenes.animate({
				top: "-=122"
			}, 500); 
			hint.animate({
				top: "-=122"
			}, 500);
		}
		gm_dropdown = false;
		hint.fadeIn(500, 0.0);
	}
}

// --------------------------------------------------------------------

function openSettingsDropdown(force=false) {
	var scenes = $('#settingsdrop');
	var hint   = $('#settingshint');
	if (force || !settings_dropdown) {
		// load zooming flag
		$('#zooming').prop('checked', zooming);
		
		scenes.animate({
			right: "+=110"
		}, 500);
		hint.animate({
			right: "+=100"
		}, 500);
	}
	settings_dropdown = true;
	hint.fadeOut(500, 0.0);   
	
	closeGmDropdown(force);
}

function closeSettingsDropdown(force=false) {
	var scenes = $('#settingsdrop');
	var hint   = $('#settingshint');
	if (scenes != null) {
		if (force || settings_dropdown) {
			scenes.animate({
				right: "-=110"
			}, 500); 
			hint.animate({
				right: "-=100"
			}, 500);
		}
		settings_dropdown = false;
		hint.fadeIn(500, 0.0);
	}
}

