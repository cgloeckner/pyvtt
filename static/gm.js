/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/

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
			// wait for sanizized gm url (as confirm)
			if (response['url'] == null) {
				showError(response['error']);
				
				// shake input
				$('#gmname').addClass('shake');
				setTimeout(function() {	$('#gmname').removeClass('shake'); }, 1000);
				
			} else {
				// redirect
				window.location = '/';
			}
		}, error: function(response, msg) {
			handleError(response);
		}
	});
}

function kickPlayers(url) {
	var kick = confirm("KICK ALL PLAYERS?");
	if (kick) {
		$.post(url='/vtt/kick-players/' + url);
	}
}

function kickPlayer(url, uuid) {
	var kick = confirm("KICK THIS PLAYER?");
	if (kick) {
		$.post(url='/vtt/kick-player/' + url + '/' + uuid);
	}
}

function deleteGame(url) {
	$.post(
		url='/vtt/delete-game/' + url,
		success=function(data) {
			$('#gmdrop')[0].innerHTML = data;
		}
	);
}

function GmUploadDrag(event) {
	event.preventDefault();
}

function GmUploadDrop(event, url_regex, gm_url) {
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
		showError('NO SPECIAL CHARS OR SPACES');
		
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
			url_ok  = response['url_ok'];
			file_ok = response['file_ok'];
			
			if (!url_ok) {
				showError(response['error']);
				
				// shake URL input
				$('#url').addClass('shake');
				setTimeout(function() {	$('#url').removeClass('shake'); }, 1000);
				
			} else {
				if (!file_ok) { 
					showError(response['error']);
					
					// reset uploadqueue
					$('#uploadqueue').val("");
					
					// reset and shake URL input
					$('#dropzone').addClass('shake');
					setTimeout(function() {	$('#dropzone').removeClass('shake'); }, 1000);
				
				} else {
					// load game
					window.location = '/' + response['url'];
				}
			}
		}, error: function(response, msg) {
			handleError(response);
		}
	});
}

// --- GM ingame tokenbar handles -------------------------------------

function addScene() {
	$.post(
		url='/vtt/create-scene/' + game_url,
		success=function(data) {
			$('#gmdrop')[0].innerHTML = data; 
		}
	);
}

function activateScene(scene_id) {
	$.post(
		url='/vtt/activate-scene/' + game_url + '/' + scene_id,
		success=function(data) {       
			$('#gmdrop')[0].innerHTML = data;
		}
	);
}

function cloneScene(scene_id) {                                                                  
	$.post(
		url='/vtt/clone-scene/' + game_url + '/' + scene_id,
		success=function(data) { 
			$('#gmdrop')[0].innerHTML = data;
		}
	);
}

function deleteScene(scene_id) {
	$.post(
		url='/vtt/delete-scene/' + game_url + '/' + scene_id,
		success=function(data) {
			$('#gmdrop')[0].innerHTML = data;
		}
	);
}
