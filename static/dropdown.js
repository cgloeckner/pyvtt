function openDropdown(force=false) {
	var scenes = $('#preview');
	var hint   = $('#drophint');
	if (force || !dropdown) {
		scenes.animate({
			top: "+=100"
		}, 500);
		hint.animate({
			top: "+=100"
		}, 500);
	}
	dropdown = true;
	hint.fadeOut(500, 0.0);
}

function closeDropdown(force=false) {
	var scenes = $('#preview'); 
	var hint   = $('#drophint');
	if (force || dropdown) {
		scenes.animate({
			top: "-=100"
		}, 500); 
		hint.animate({
			top: "-=100"
		}, 500);
	}
	dropdown = false;
	hint.fadeIn(500, 0.0);
}
