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
	
	closehistoryDropdown(force);
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

function toggleHistoryDropdown() {
	var scenes = $('#historydrop');
	var hint   = $('#historyhint');
	if (history_dropdown) {
		// close history
		scenes.animate({
			right: "-=105"
		}, 500); 
		history_dropdown = false;
	} else {
		// show history
		scenes.animate({
			right: "+=105"
		}, 500);
		history_dropdown = true;
	}
}

