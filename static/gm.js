function registerGm(event) {
	event.preventDefault();
	
	var gmname = $('#gmname').val();
	
	$.ajax({
		type: 'POST',
		url:  '/vtt/join',
		dataType: 'json',
		data: {
			'gmname' : gmname
		},
		success: function(response) {
			// wait for sanizized input
			gmname = response['gmname']
			
			if (gmname == '') {
				// shake input
				$('#gmname').addClass('shake');
				setTimeout(function() {	$('#gmname').removeClass('shake'); }, 1000);
				
			} else {
				// redirect
				window.location = '/';
			}
		}
	});
}

function deleteGame(url) {
	$.post(
		url='/vtt/delete-game/' + url,
		success=function(data) {
			$('#preview')[0].innerHTML = data;
		}
	);
}

function GmUploadDrag(event) {
	event.preventDefault();
}

function GmUploadDrop(event, url_regex, gm_name) {
	event.preventDefault();
	
	// fetch upload data
	var queue = $('#uploadqueue')[0];
	queue.files = event.dataTransfer.files;
	var f = new FormData($('#uploadform')[0]);
	
	var url = $('#url').val();
	if (url == '') {
		// generate url from filename
		// note: single-file-upload
		var fname = event.dataTransfer.files[0].name;
		var parts = fname.split('.');
		var ext   = parts[parts.length - 1];
		url   = fname.replace('.' + ext, '')
		$('#url').val(url);
	}
	
	// check url via regex
	r = new RegExp(url_regex, 'g');
	if (!r.test(url)) { 
		// shake URL input
		$('#url').addClass('shake');
		setTimeout(function() {	$('#url').removeClass('shake'); }, 1000);
		return;
	}
	
	// import game
	$.ajax({
		url: '/vtt/import-game/' + url,
		type: 'POST',
		data: f,
		contentType: false,
		cache: false,
		processData: false,
		success: function(response) {
			console.log(response);
			url_ok  = response['url'];
			file_ok = response['file'];
			
			if (!url_ok) {
				// shake URL input
				$('#url').addClass('shake');
				setTimeout(function() {	$('#url').removeClass('shake'); }, 1000);
			} else {
				if (!file_ok) {
					// reset uploadqueue
					$('#uploadqueue').val("");
					
					// reset and shake URL input
					$('#dropzone').addClass('shake');
					setTimeout(function() {	$('#dropzone').removeClass('shake'); }, 1000);
				
				} else {
					// load game
					window.location = '/' + gm_name + '/' + url;
				}
			}
		}
	});
}
