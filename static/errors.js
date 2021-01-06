/** Powered by PyVTT. Further information: https://github.com/cgloeckner/pyvtt **/
  
function showError(msg) {
	var error = $('#error');
	error[0].innerHTML = msg;
	if (error.css('display') == 'none') {
		error.fadeIn(100, 0.0);
		error.delay(7000).fadeOut(3000, 0.0);
	}
}
