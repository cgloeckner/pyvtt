/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/

var socket = null; // websocket used for client-server-interaction
var quiet = true;

var ping_delay = 2000; // delay between two pings
var next_ping  = null; // indicates when the next ping will be sent
var last_ping  = null; // timestamp when last ping was sent

var socket_move_delay = 100;
var socket_move_timeout = 0; // delay until the next move update will be sent through the socket

// --- game state implementation ----------------------------------------------

var game_url = '';
var gm_name = '';
var gm_dropdown = false; // GM's scenes view
var history_dropdown = false; // roll history
var timeid = 0;
var full_update = true;
var scene_id = 0;
var is_gm = false;

var max_token_size = null;
var max_background_size = null;

var my_uuid = '';

/// Handle function for interaction via socket
function onSocketMessage(event) {
	var data = JSON.parse(event.data);
	if (!quiet) {
		console.info(data);
	}
	var opid = data.OPID;
	
	switch (opid) { 
		case 'PING':
			onPing(data);
			break;
		case 'ACCEPT':
			onAccept(data);
			break;  
		case 'UPDATE':
			onUpdate(data);
			break;
		case 'CREATE':
			onCreate(data);
			break;
		case 'DELETE':
			onDelete(data);
			break;
		case 'REFRESH':
			onRefresh(data);
			break;
		case 'JOIN':
			onJoin(data);
			break;
		case 'QUIT':
			onQuit(data);
			break;
		case 'ROLL':
			onRoll(data);
			break;
		case 'SELECT':
			onSelect(data);
			break;
		case 'ORDER':
			onOrder(data);
			break;
		default:
			console.error('Invalid OpID "' + opid + '"');
	};
}

function onAccept(data) {
	my_uuid = data['uuid'];
	
	// show all players
	$.each(data.players, function(i, details) {
		var p = new Player(details.name, details.uuid, details.color, details.ip, details.country, details.index);
		p.is_last = p.index == data.players.length - 1;
		showPlayer(p);
	});
	
	// show all rolls
	$.each(data.rolls, function(item, obj) {
		addRoll(obj.sides, obj.result, obj.name, obj.color, obj.recent);
	});
	
	onRefresh(data);
	
	updateTokenbar();
}

function onUpdate(data) {
	var is_primary = false;
	
	$.each(data.tokens, function(index, token) {
		updateToken(token);
		
		if (token.id == primary_id) {
			is_primary = true;
		}
	});
	
	if (is_primary) {
		updateTokenbar();
	}
}

function onCreate(data) {
	$.each(data.tokens, function(index, token) {
		updateToken(token, true);
		
		tokens_added[token.id] = 0.0;
	});
}

function onDelete(data) {
	$.each(data.tokens, function(index, token) {
		// overwrite new position with current
		// (this will prevent from fading out at (0|0)
		token.newx = token.posx;
		token.newy = token.posy;
		
		delete tokens[token.id];
		
		tokens_removed[token.id] = [token, 1.0];
	});

}

function onJoin(data) {
	var p = new Player(data.name, data.uuid, data.color, data.ip, data.country, data.index);
	showPlayer(p);
}

function onQuit(data) {
	hidePlayer(data.uuid); 
}

function onRoll(data) {
	addRoll(data.sides, data.result, data.name, data.color, data.recent);
}

function onSelect(data) {
	player_selections[data.color] = data.selected;
	
	// update player's primary selection
	if (data.color == getCookie('playercolor') && data.selected.length > 0) {
		select_ids = data.selected;
		if (!select_ids.includes(primary_id)) {
			// reselect primary item (previous one does not belong to new selection)
			primary_id = data.selected[0];
		}
	}
}

function onOrder(data) {
	$.each(data.indices, function(uuid, index) {
		players[uuid].index = index;
		players[uuid].is_last = index == Object.keys(data.indices).length - 1;
	});
	
	rebuildPlayers();
}

function onRefresh(data) {
	resetViewport();
	
	// show drop hint again
	$('#draghint').show();
	
	// reset tokens               
	background_set = false;
	tokens = [];
	$.each(data.tokens, function(index, token) {
		updateToken(token, true);
	});
}

/// Send data JSONified to server via the websocket
function writeSocket(data) {
	var raw = JSON.stringify(data);
	if (!quiet) {
		console.info(data);
	}
	socket.send(raw);
}

/// Called after drawing to update ping if necessary
function updatePing() {
	var now = Date.now();
	if (now >= next_ping) {
		// trigger next ping
		next_ping = now + ping_delay;
		last_ping = now;
		writeSocket({'OPID': 'PING'});
	}
}

/// Event handle to react on server's ping reply
function onPing(data) {
	// calculate time since ping request
	var now   = Date.now();
	var delta = now - last_ping;
	$('#ping')[0].innerHTML = 'PING: ' + delta + 'ms';
}

/// Handles login and triggers the game
function login(event, gmname, url, websocket_url, as_gm) {
	event.preventDefault();
	
	$('#popup').hide();
	
	var playername  = $('#playername').val();
	var playercolor = $('#playercolor').val();
	
	$.ajax({
		type: 'POST',
		url:  '/' + gmname + '/' + url + '/login',
		dataType: 'json',
		data: {
			'playername'  : playername,
			'playercolor' : playercolor
		},
		success: function(response) {
			// wait for sanizized input
			error       = response['error']
			playername  = response['playername']
			playercolor = response['playercolor']
			
			if (error != '') {
				showError(error);
				
				$('#playername').addClass('shake');
				setTimeout(function() {	$('#playername').removeClass('shake'); }, 1000);
				
			} else {
				$('#historydrop').hide();
				
				// hide login screen
				$('#game').fadeIn(1000, 0.0);
				
				$('#login').fadeOut(1000, 0.0, function() {
					$('#login').hide();
					
					// show players
					$('#mapfooter').css('display', 'block');
					$('#mapfooter').animate({ opacity: '+=1.0' }, 2000);
					
					// show dicebox
					$('#dicebox').css('display', 'block');
					$('#dicebox').animate({ opacity: '+=1.0' }, 2000);
					
					onWindowResize();
				});
				
				resetViewport();
				
				max_background_size = response['file_limit']['background'];
				max_token_size      = response['file_limit']['token'];
				
				// start socket communication
				socket = new WebSocket(websocket_url)
				
				socket.onmessage = onSocketMessage;
				
				socket.onopen = function() { 
					is_gm = as_gm;
					
					start(gmname, url, playername, playercolor);
				};
				
				socket.onclose = function(event) {
					$('#game').fadeOut(1000, 0.0);
					
					// forget everything about the old session
					images            = [];
					tokens            = [];
					tokens_added      = [];
					tokens_removed    = [];
					player_selections = {};
					culling           = [];
					players           = {};
					rolls             = []; 
					copy_tokens       = [];
					select_ids        = [];
					is_gm             = false;
					
					max_background_size = null;
					max_token_size      = null;
					
					$.each([2, 4, 6, 8, 10, 12, 20], function(index, sides) {
						var d = $('#d' + sides + 'rolls');
						d[0].innerHTML = '';
					});
					
					// return to login screen
					$('#login').fadeIn(1000, 0.0, function() {
						showError('CONNECTION LOST');
					});
				};
			}
		}, error: function(response, msg) {
			if ('responseText' in response) {
				handleError(response);
			} else {
				showError('SERVER NOT FOUND');
			}
		}
	});
}

/// Sets up the game and triggers the update loop
function start(gmname, url, playername, color) {
	writeSocket({
		'name'     : playername,
		'gm_url'   : gmname,
		'game_url' : url
	});
	
	// setup in-memory canvas (for transparency checking)
	mem_canvas = document.createElement('canvas');
	
	// disable window context menu for token right click
	document.addEventListener('contextmenu', event => {
		event.preventDefault();
	});
	
	// drop zone implementation (using canvas) --> also as players :) 
	battlemap.addEventListener('dragover',	onDrag);
	battlemap.addEventListener('drop', 		onDrop);
	
	// desktop controls
	battlemap.addEventListener('mousedown',	onGrab);
	document.addEventListener('mousemove',	onMove);
	document.addEventListener('mouseup',	onRelease);
	battlemap.addEventListener('wheel',		onWheel);
	battlemap.addEventListener('mouseout',	onRelease);
	document.addEventListener('keydown',	onShortcut);
	document.addEventListener('keyup',		onKeyRelease);
	
	$(window).resize(onWindowResize);
	
	// setup game  
	gm_name = gmname;
	game_url = url;
	
	drawScene();
}
