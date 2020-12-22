function registerGm() {
	var gmname = $('#gmname').val();
	
	$.ajax({
		type: 'POST',
		url:  '/vtt/register',
		dataType: 'json',
		data: {
			'gmname' : gmname
		},
		success: function(response) {
			// wait for sanizized input
			gmname = response['gmname']
			
			if (gmname == '') {
				$('#gmname').addClass('shake');
				setTimeout(function() {	$('#gmname').removeClass('shake'); }, 1000);
				
			} else {
				window.location = '/';
			}
		}
	});
}

function createGame() {
	var url = $('#url').val();
	
	$.ajax({
		type: 'POST',
		url:  '/vtt/create-game',
		dataType: 'json',
		data: {
			'url' : url
		},
		success: function(response) {
			// wait for sanizized input
			url  = response['url']
			
			if (url == '') {
				$('#url').addClass('shake');
				setTimeout(function() {	$('#url').removeClass('shake'); }, 1000);
				
			} else {
				window.location.reload()
			}
		}
	});
}

function GmUploadDrag(event) {
	event.preventDefault();
}

function GmUploadDrop(event) {
	event.preventDefault();
	
	var queue = $('#uploadqueue')[0];
	queue.files = event.dataTransfer.files;
	
	var f = new FormData($('#uploadform')[0]);
	console.log(event.dataTransfer.files);
	
	$.ajax({
		url: '/vtt/import-game',
		type: 'POST',
		data: f,
		contentType: false,
		cache: false,
		processData: false,
		success: function(response) {
			// response tells actual URLs per ZIP, but this is ignored here atm
			window.location.reload();
		}
	});
}

/*
function importGame() {
	var url = $('#url').val();
	var file = $('#archive')[0].value;
	
	if (file == '') {
		$('#archive').addClass('shake');
		setTimeout(function() {	$('#archive').removeClass('shake'); }, 1000);
		return;
	}
	
	var data = new FormData($('#import')[0]);
	
	$.ajax({
		url: '/vtt/import-game/' + url,
		type: 'POST',
		data: data,
		contentType: false,
		cache: false,
		processData: false,
		success: function(response) {
			// reset upload queue
			// wait for sanizized input
			url  = response['url']
			
			if (url == '') {
				$('#url').addClass('shake');
				setTimeout(function() {	$('#url').removeClass('shake'); }, 1000);
				
			} else {
				//window.location = 
			}
		}
	});
}
*/
