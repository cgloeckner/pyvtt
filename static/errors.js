/** Powered by PyVTT. Further information: https://github.com/cgloeckner/pyvtt **/
  
function showError(msg) {
	console.warn(msg);
	
	var error = $('#error');
	error[0].innerHTML = msg;
	if (error.css('display') == 'none') {
		error.fadeIn(100, 0.0);
		error.delay(7000).fadeOut(3000, 0.0);
	}
}

function handleError(response) {
	// parse error_id from response
	var error_id = response.responseText.split('<pre>')[1].split('</pre>')[0]
	
	// redirect to error page
	window.location = '/vtt/error/' + error_id;
}
