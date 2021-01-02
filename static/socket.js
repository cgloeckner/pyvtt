/** Powered by PyVTT. Further information: https://github.com/cgloeckner/pyvtt **/

var socket = null; // websocket used for client-server-interaction
var quiet = true;

// --- game state implementation ----------------------------------------------

var game_url = '';
var gm_name = '';
var dropdown = false;
var timeid = 0;
var full_update = true;
var scene_id = 0;

/// Handle function for interaction via socket
function onSocketMessage(event) {
	var data = JSON.parse(event.data);
	if (!quiet) {
		console.log(data);
	}
	var opid = data.OPID;
	
	switch (opid) { 
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
			onDice(data);
			break;
		case 'SELECT':
			onSelect(data);
			break;
		default:
			console.log('Error: Invalid OpID');
	};
}

function onAccept(data) {
	// show all players
	$.each(data.players, function(name, details) {
		showPlayer(name, details.uuid, details.color, details.country); // uuid, color
	});
	
	// show all rolls
	$.each(data.rolls, function(item, obj) {
		addRoll(obj.sides, obj.result, obj.color);
	});
	
	onRefresh(data);
	
	updateTokenbar();
}

function onUpdate(data) {
	$.each(data.tokens, function(index, token) {
		updateToken(token);
	});
}

function onCreate(data) {
	$.each(data.tokens, function(index, token) {
		updateToken(token);
		
		tokens_added[token.id] = 0.0;
	});
}

function onDelete(data) {
	$.each(data.tokens, function(index, token) {
		delete tokens[token.id];
		
		tokens_removed[token.id] = [token, 1.0];
	});
}

function onJoin(data) {
	var name    = data.name;
	var uuid    = data.uuid;
	var color   = data.color
	var country = data.country;
	showPlayer(name, uuid, color, country); 
}

function onQuit(data) {
	var name  = data.name;
	var uuid  = data.uuid;
	players[name] = null;
	hidePlayer(name, uuid); 
}

function onDice(data) {
	addRoll(data.sides, data.result, data.color, data.roll_id);
}

function onSelect(data) {
	player_selections[data.color] = data.selected;
	
	// update player's primary selection
	if (data.color == getCookie('playercolor') && data.selected.length > 0) {
		select_ids = data.selected;
		primary_id = data.selected[0];
	}
}

function onRefresh(data) {
	// reset tokens               
	background_set = false;
	tokens = [];
	$.each(data.tokens, function(index, token) {
		updateToken(token);
	});
}

/// Send data JSONified to server via the websocket
function writeSocket(data) {
	var raw = JSON.stringify(data);
	socket.send(raw);
}

/// Handles login and triggers the game
function login(event, gmname, url, server_url) {
	event.preventDefault();
	
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
			playername  = response['playername']
			playercolor = response['playercolor']
			
			if (playername == '') {
				$('#playername').addClass('shake');
				setTimeout(function() {	$('#playername').removeClass('shake'); }, 1000);
				
			} else {
				// hide login screen
				$('#drophint').fadeIn(1000, 0.0);
				
				$('#login').fadeOut(1000, 0.0, function() {
					$('#login').hide();
					
					// show players
					$('#mapfooter').css('display', 'block');
					$('#mapfooter').animate({ opacity: '+=1.0' }, 2000);
					
					// show dicebox
					$('#dicebox').css('display', 'block');
					$('#dicebox').animate({ opacity: '+=1.0' }, 2000);
				});
				
				// start socket communication
				// @TODO: query server name and port   
				socket = new WebSocket('ws://' + server_url + '/websocket')
				
				socket.onmessage = onSocketMessage;
				
				socket.onopen = function() {
					start(gmname, url, playername, playercolor);
				};
				
				socket.onclose = function(event) {
					$('#drophint').fadeOut(1000, 0.0);
					
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
					viewport.left     = 0;
					viewport.top      = 0;
					viewport.zoom     = 1.0;
					
					$('#d4box')[0].innerHTML   = '';
					$('#d6box')[0].innerHTML   = '';
					$('#d8box')[0].innerHTML   = '';
					$('#d10box')[0].innerHTML  = '';
					$('#d12box')[0].innerHTML  = '';
					$('#d20box')[0].innerHTML  = '';
					$('#players')[0].innerHTML = '';
					
					// return to login screen
					$('#login').fadeIn(1000, 0.0, function() {
						alert('CONNECTION LOST');
					});
				};
			}
		}
	});
}

/// Sets up the game and triggers the update loop
function start(gmname, url, playername, color) {
	writeSocket({
		'name'  : playername,
		'url'   : gmname + '/' + url
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
	battlemap.addEventListener('mousemove',	onMove);
	battlemap.addEventListener('mouseup',	onRelease);
	battlemap.addEventListener('wheel',		onWheel);
	battlemap.addEventListener('mouseout',	onRelease);
	document.addEventListener('keydown',	onShortcut);
	
	// setup game  
	gm_name = gmname;
	game_url = url;
	
	drawScene();
}
