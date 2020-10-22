
// --- image handling implementation ------------------------------------------

var images = [];
var canvas_scale = 1.0; // saved scaling

function resizeCanvas() {
	var canvas = $('#battlemap');
	
	// avoid breaking aspect ratio
	// note: avoids tokens to be out of view for some players
	var w = window.innerWidth - 10;
	var h = w * 0.56;
	
	// handle too large height
	if (h > window.innerHeight - 65) {
		h = window.innerHeight - 65;
		w = h / 0.56;
	}
	
	// apply size
	canvas[0].width  = w;
	canvas[0].height = h;
	
	// calculate scaling
	canvas_scale = w / 1000;
}

/// Will clear the canvas
function clearCanvas() {
	var canvas = $('#battlemap');
	var context = canvas[0].getContext("2d");
	
	resizeCanvas();
	
	context.save();
	context.clearRect(0, 0, canvas[0].width, canvas[0].height);
	context.restore();
}

var mem_canvas = null;

/// Get image pixel data
function getPixelData(token, x, y) {
	// note: tokens are drawn centered
	// x, y is relative to the token position
	
	var dom_canvas = $('#battlemap')[0];
	
	// setup in-memory canvas (x1.414 due to extreme rotation and pythagoras)
	var size = token.size * 1.415;
	mem_canvas = document.createElement('canvas');
	mem_canvas.width  = size;
	mem_canvas.height = size;

	// query clean context
	var mem_ctx = mem_canvas.getContext('2d');
	mem_ctx.clearRect(0, 0, size, size);
	
	// draw image (scaled and rotated)
	sizes = getActualSize(token, dom_canvas.width, dom_canvas.height);
	mem_ctx.save();
	mem_ctx.translate(sizes[0] / 2, sizes[1] / 2);
	mem_ctx.rotate(token.rotate * 3.14/180.0);
	// note: drawn centered for proper rotation
	mem_ctx.drawImage(images[token.url], -sizes[0] / 2, -sizes[1] / 2, sizes[0], sizes[1]);
	
	// query pixel data
	// note: consider (x,y) is relative to token's center
	return mem_ctx.getImageData(x + sizes[0] / 2, y + sizes[1] / 2, 1, 1).data;
}

// --- token implementation ---------------------------------------------------

var tokens       = []; // holds all tokens, updated by the server
var change_cache = []; // holds ids of all client-changed tokens

var player_selections = []; // contains selected tokens and corresponding player colors

var culling = []; // holds tokens for culling
var min_z = -1; // lowest known z-order
var max_z =  1; // highest known z-order
var min_token_size = 80;

/// Token constructor
function Token(id, url) {
	this.id = id;
	this.posx = 0;
	this.posy = 0;
	this.zorder = 0;
	this.size = 250;
	this.url = url;
	this.rotate = 0.0;
	this.locked = false;
}

/// Add token with id and url to the scene
function addToken(id, url) {
	tokens[id] = new Token(id, url);
}

/// Calculate actual token size
function getActualSize(token, maxw, maxh) {
	var src_h = images[token.url].height;
	var src_w = images[token.url].width;
	var ratio = src_w / src_h;
	
	// scale token via width (most common usecase)
	var w = token.size;
	var h = w / ratio;
	if (token.size == -1) {
		if (ratio > 0.56) {
			w = maxw / canvas_scale;
			h = w / ratio;
		} else {
			h = maxh / canvas_scale;
			w = h * ratio;
		}
		
	} else if (src_h > src_w) {
		// scale token via height
		h = token.size;
		w = h * ratio;
	}
	
	return [w, h];
}

/// Determiens if position is within token's bounding box
function isOverToken(x, y, token) {
	// 1st stage: bounding box test
	if (token.size > 0) {
		var min_x = token.posx - token.size / 2;
		var max_x = token.posx + token.size / 2;
		var min_y = token.posy - token.size / 2;
		var max_y = token.posy + token.size / 2;
		var in_box = min_x <= x && x <= max_x && min_y <= y && y <= max_y;
		if (!in_box) {
			return false;
		}
	}
	// 2nd stage: image alpha test
	// note: query at position relative to token's center
	var dx = x - token.posx;
	var dy = y - token.posy;
	var pixel_data = getPixelData(token, dx, dy);
	return pixel_data[3] > 0;
}

/// Determines which token is selected when clicking the given position
function selectToken(x, y) {
	var result = null;	
	var bestz = min_z - 1;
	// search for any fitting culling with highest z-order (unlocked first)
	$.each(culling, function(index, item) {
		if (item != null && !item.locked && item.zorder > bestz && isOverToken(x, y, item)) {
			bestz  = item.zorder;
			result = item;
		}
	});
	if (result == null) {
		// try locked tokens next
		$.each(culling, function(index, item) {
			if (item != null && item.locked && item.zorder > bestz && isOverToken(x, y, item)) {
				bestz  = item.zorder;
				result = item;
			}
		});
	}
	return result;
}

/// Update token data for the provided token (might create a new token)
function updateToken(data) {
	// create token if necessary
	if (!tokens.includes(data.id)) {
		addToken(data.id, data.url);
	}
	
	// update token data
	tokens[data.id].posx   = data.posx;
	tokens[data.id].posy   = data.posy;
	tokens[data.id].zorder = data.zorder;
	tokens[data.id].size   = data.size;
	tokens[data.id].rotate = data.rotate;
	tokens[data.id].locked = data.locked;
	
	if (data.zorder < min_z) {
		min_z = data.zorder;
	}
	if (data.zorder > max_z) {
		max_z = data.zorder;
	}
	
	if (data.size == -1) {
		// align background image to center
		var canvas = $('#battlemap');
		tokens[data.id].posx = canvas[0].width  / 2 / canvas_scale;
		tokens[data.id].posy = canvas[0].height / 2 / canvas_scale;
	}
}

/// Draws a single token (show_ui will show the selection box around it)
function drawToken(token, color) {
	var canvas = $('#battlemap');
	var context = canvas[0].getContext("2d");
	
	// cache image if necessary
	if (!images.includes(token.url)) {
		images[token.url] = new Image();
		images[token.url].src = token.url;
	}
	
	var sizes = getActualSize(token, canvas[0].width, canvas[0].height);
	sizes[0] *= canvas_scale;
	sizes[1] *= canvas_scale;
	
	// draw image
	context.save();
	context.translate(token.posx * canvas_scale, token.posy * canvas_scale);
	context.rotate(token.rotate * 3.14/180.0);
	
	if (color != null) {
		context.shadowColor = color;
		context.shadowBlur = 25;
	}
	
	context.drawImage(images[token.url], -sizes[0] / 2, -sizes[1] / 2, sizes[0], sizes[1]);
	
	context.restore();
}

// --- player implementation --------------------------------------------------

var players = {};

function getCookie(key) {
	var arr = document.cookie.split(key + '=')[1];
	if (arr == null) {
		return '';
	}
	return arr.split('; ')[0];
}

function setCookie(key, value) {
	// magical cookie properties :)
	// this REALLY appends / updates based on the current cookie
	document.cookie = key + '=' + value;
}

function updatePlayers(response) {
	var own_name = getCookie('playername');
	
	// parse players to key-value pairs (name => color)
	var current = {};
	$.each(response, function(index, line) {
		var parts = line.split(':');
		name  = parts[0];
		color = parts[1];
		current[name] = color;
		
		if (players[name] == null) {
			// add new player
			players[name] = color;
			console.log(name, 'joined');
			
			var container = '<span id="player_' + name + '" class="player" style="filter: drop-shadow(1px 1px 9px ' + color + ') drop-shadow(-1px -1px 0 ' + color + ');">';
			if (name == own_name) {
				container += '<a href="/play/' + game_url + '/logout" title="Logout">' + name + '</a>';
			} else {
				container += name;
			}
			container += '</span>';
			$('#players').append(container);
		}
	});
	
	// show players
	$.each(players, function(name, color) {
		if (color != null && current[name] == null) {
			// remove existing player
			players[name] = null;
			console.log(name, 'left');
			
			$('#player_' + name).remove();
		}
	});
}


// --- dice rolls implementation ---------------------------------------------- 

var rolls   = [];

/// Roll constructor
function Roll(sides, playername, result) {
	this.sides      = sides;
	this.playername = player;
	this.result     = result;
}

function showRoll(sides, result, player, color, time) {
	var target = $('#rollbox')[0];
	var div_class = 'roll';
	if (result == 1) {
		div_class += ' min-roll';
	}
	if (result == sides) {
		div_class += ' max-roll';
	}
	target.innerHTML += '<div class="' + div_class + '"><img src="/static/d' + sides + '.png" style="filter: drop-shadow(1px 1px 10px ' + color + ') drop-shadow(-1px -1px 0 ' + color + ');"/><span class="result" style="color: ' + color + ';">' + result + '</span><span class="player" style="color: ' + color + '">' + player + ' (' + time + ')</span></div>';
}

function updateRolls(rolls) {
	// show rolls
	var rolls_div = $('#rollbox')[0];
	rolls_div.innerHTML = '';
	$.each(rolls, function(index, roll) {
		showRoll(roll['sides'], roll['result'], roll['player'], roll['color'], roll['time']);
	});		
}

/*
function updateRolls(rolls) {
	// show rolls
	$('#roll4')[0].innerHTML = '';
	$('#roll6')[0].innerHTML = '';
	$('#roll8')[0].innerHTML = '';
	$('#roll10')[0].innerHTML = '';
	$('#roll12')[0].innerHTML = '';
	$('#roll20')[0].innerHTML = '';
	$.each(rolls, function(index, roll) {
		showRoll(roll['sides'], roll['result'], roll['color']);
	});
}

function showRoll(sides, result, color) {
	var raw = '<div class="roll';
	if (result == sides) {
		raw += ' max-roll';
	} else if (result == 1) {
		raw += ' min-roll';
	}
	raw += '" style="color: ' + color + ';">' + result + '</div>';

	if (sides == 100) {
		sides = 10;
	}
	$('#roll' + sides)[0].innerHTML += raw;
	
	return $('#roll' + sides)[0]; 
}
*/

// --- game state implementation ----------------------------------------------

var game_url = '';
var timeid = 0;

var mouse_x = 0; // relative to canvas
var mouse_y = 0;

var copy_token = 0; // determines copy-selected token (CTRL+C)
var select_id = 0; // determines selected token
var mouse_over_id = 0; // determines which token would be selected
var grabbed = 0; // determines whether grabbed or not
var update_tick = 0; // delays updates to not every loop tick
var full_tick = 0; // counts updates until the next full update is requested

const fps = 60;

/// Triggers token updates (pushing and pulling token data via the server)
function updateTokens() {
	// fetch all changed tokens' data
	var changes = [];
	$.each(change_cache, function(index, token_id) {
		// copy token to update-data
		var t = tokens[token_id];
		var data = {
			'id'    : t.id,
			'posx'  : t.posx,
			'posy'  : t.posy,
			'zorder': t.zorder,
			'size'  : t.size,
			'rotate': t.rotate,
			'locked': t.locked
		};
		changes.push(data);
	});
	
	// fake zero-timeid if full update is requested
	if (full_tick == 0) {
		timeid = 0;
		full_tick = 5;
	} else {
		full_tick -= 1;
	}
	
	// start update with server
	$.ajax({
		type: 'POST',
		url:  '/play/' + game_url + '/update',
		dataType: 'json',
		data: {
			'timeid'   : timeid,
			'changes'  : JSON.stringify(changes),
			'selected' : select_id
		},
		success: function(response) {		
			// update current timeid
			timeid = response['timeid'];
			
			// clear all local tokens if a full update was received
			if (response['full']) {
				tokens = [];
			}
			
			// update tokens
			$.each(response['tokens'], function(index, token) {
				updateToken(token);
			});
			
			updateTokenbar();
			updateRolls(response['rolls']);
			updatePlayers(response['players']);
			
			// highlight token selection (switch key and value, see server impl)
			player_selections = [];
			$.each(response['selected'], function(color, tokenid) {
				player_selections.push([tokenid, color]);
			});
			
			// reset changes
			change_cache = [];
			
		}
	});
}

/// Draw the entire scene (locked tokens in the background, unlocked in foreground)
function drawScene() {
	clearCanvas();
	
	// add all tokens to regular array
	culling = [];
	var background = null;
	$.each(tokens, function(index, token) {
		if (token != null) {
			if (token.size == -1) {
				background = token;
			} else {
				culling.push(token);
			}
		}
	});
	
	// sort tokens by z-order
	culling.sort(function(a, b) { return a.zorder - b.zorder });
	
	// draw tokens
	if (background != null) {
		drawToken(background, background.id == select_id);
	}
	$.each(culling, function(index, token) {
		var color = null;
		$.each(player_selections, function(index, arr) {
			if (arr[0] == token.id) {
				color = arr[1];
			}
		});
		if (color == null && token.id == select_id) {
			color = getCookie('playercolor');
		}
		drawToken(token, color);
	});
	
	// reverse culling for top-to-bottom token searching
	culling.reverse();
}

/// Updates the entire game: update tokens from time to time, drawing each time
function updateGame() {
	if (update_tick < 0) {
		updateTokens();
		update_tick = 250.0 / (1000.0 / fps);
	} else {
		update_tick -= 1;
	}
	
	drawScene();
	setTimeout("updateGame()", 1000.0 / fps);
}

/// Sets up the game and triggers the update loop
function start(url) {
	game_url = url;
	
	// notify game about this player
	navigator.sendBeacon('/play/' + game_url + '/join');
	
	// show gm toolbar
	if (getCookie('dropdown') == 'show') {
		toggleDropdown();
	}
	
	updateGame();
}

/// Handles disconnecting
function disconnect() {
	// note: only works if another tab stays open
	navigator.sendBeacon('/play/' + game_url + '/disconnect');
}

function uploadDrag(event) {
	event.preventDefault();
}

function uploadDrop(event) {
	event.preventDefault();
	pickCanvasPos(event);
	
	var queue = $('#uploadqueue')[0];
	queue.files = event.dataTransfer.files;
	
	var f = new FormData($('#uploadform')[0]);
	
	$.ajax({
		url: '/play/' + game_url + '/upload/' + mouse_x + '/' + mouse_y,
		type: 'POST',
		data: f,
		contentType: false,
		cache: false,
		processData: false,
		success: function(response) {
			// reset upload queue
			$('#uploadqueue').val("");
		}
	});
}

function showTokenbar(token_id) {
	if (mouse_over_id == token_id) {
		$('#tokenbar').css('visibility', 'visible');
	} else {
		$('#tokenbar').css('visibility', 'hidden');
		setTimeout("showTokenbar(" + mouse_over_id + ")", 500.0);
	}
}

function updateTokenbar() {
	// query mouse over token
	var token = selectToken(mouse_x, mouse_y);
	if (token != null) {
		mouse_over_id = token.id;
		if (!grabbed) {
			// update tokenbar if not grabbed
			
			// show tokenbar delayed
			setTimeout("showTokenbar(" + token.id + ")", 500.0);
			
			// cache image if necessary
			if (!images.includes(token.url)) {
				images[token.url] = new Image();
				images[token.url].src = token.url;
			}
		
			// image size aspect ratio
			var src_h = images[token.url].height;
			var src_w = images[token.url].width;
			var ratio = src_w / src_h;
			
			// determine token size
			var canvas = $('#battlemap');
			var size = token.size;
			if (size == -1) {
				size = canvas[0].height;
			}
			
			// position tokenbar centered to token
			var bx = canvas[0].getBoundingClientRect();
			var canvas = $('#battlemap');
			var sizes = getActualSize(token, canvas[0].width, canvas[0].height);
			$('#tokenbar').css('left', bx.left + token.posx * canvas_scale - 32 + 'px');
			$('#tokenbar').css('top',  bx.top  + token.posy * canvas_scale - 24 + 32 * token.size / min_token_size + 'px');
			
			if (token.locked) {
				$('#tokenLock')[0].src = '/static/locked.png';
				$('#tokenTop').css('visibility', 'hidden');
				$('#tokenBottom').css('visibility', 'hidden');
				$('#tokenStretch').css('visibility', 'hidden');
			} else {	
				$('#tokenLock')[0].src = '/static/unlocked.png';
				$('#tokenTop').css('visibility', '');
				$('#tokenBottom').css('visibility', '');
				$('#tokenStretch').css('visibility', '');
			}
		} else {
			// hide tokenbar when token grabbed
			$('#tokenbar').css('visibility', 'hidden');
		}
	} else {
		// hide tokenbar when no token selected
		mouse_over_id = 0;
		$('#tokenbar').css('visibility', 'hidden');
	}
}

// ----------------------------------------------------------------------------

/// Select mouse/touch position relative to the canvas
function pickCanvasPos(event) {
	if (event.changedTouches) {
		var touchobj = event.changedTouches[0];
		mouse_x = touchobj.clientX;
		mouse_y = touchobj.clientY;
	} else {
		mouse_x = event.clientX;
		mouse_y = event.clientY;
	}
	
	// make pos relative
	var bx = $('#battlemap')[0].getBoundingClientRect();
	mouse_x -= bx.left;
	mouse_y -= bx.top;
	
	mouse_x = parseInt(mouse_x / canvas_scale);
	mouse_y = parseInt(mouse_y / canvas_scale);
}

/// Event handle for start grabbing a token
function tokenGrab(event) {
	closeDropdown();
	
	pickCanvasPos(event);

	prev_id = select_id;
	select_id = 0;
	var token = selectToken(mouse_x, mouse_y);
	
	if (token != null && !token.locked) {
		if (event.buttons == 1) {
			// Left click: select token
			select_id = token.id;
			grabbed = true;
		} else if (event.buttons == 2) {
			// Right click: reset token scale & rotation
			token.rotate = 0;
			token.size   = min_token_size;
			
			// mark token as changed
			if (!change_cache.includes(token.id)) {
				change_cache.push(token.id);
			}
		}
	}
	
	updateTokenbar();
}

/// Event handle for releasing a grabbed token
function tokenRelease() {
	if (select_id != 0) {
		grabbed = false;
	}
	
	updateTokenbar();
}

/// Event handle for moving a grabbed token (if not locked)
function tokenMove(event) {
	pickCanvasPos(event);
	
	if (select_id != 0 && grabbed) {
		var token = tokens[select_id];
		if (token == null || token.locked) {
			return;
		}
		
		// update position
		token.posx = mouse_x;
		token.posy = mouse_y;
		
		// mark token as changed
		if (!change_cache.includes(select_id)) {
			change_cache.push(select_id);
		}
	}
}

/// Event handle for rotation and scaling of tokens (if not locked)
function tokenWheel(event) {
	if (select_id != 0) {
		var token = tokens[select_id];
		if (token.locked) {
			return;
		}

		if (event.shiftKey) {
			// handle scaling
			token.size = token.size - 5 * event.deltaY;
			if (token.size > min_token_size * 5) {
				token.size = min_token_size * 5;
			}
			if (token.size < min_token_size) {
				token.size = min_token_size;
			}
				
			// mark token as changed
			if (!change_cache.includes(select_id)) {
				change_cache.push(select_id);
			}
			
		} else {
			// handle rotation
			token.rotate = token.rotate - 5 * event.deltaY;
			if (token.rotate >= 360.0 || token.rotate <= -360.0) {
				token.rotate = 0.0;
			}
			
			// mark token as changed
			if (!change_cache.includes(select_id)) {
				change_cache.push(select_id);
			}
		}
	}
	
	updateTokenbar();
}

/// Event handle to click a dice
function rollDice(sides) {
	$.post('/play/' + game_url + '/roll/' + sides);
}

/// Event handle shortcuts on tokens
function tokenShortcut(event) {
	if (event.ctrlKey) {
		if (event.keyCode == 67) { // CTRL+C
			copy_token = select_id;
		} else if (event.keyCode == 86) { // CTRL+V
			if (copy_token > 0) {
				$.post('/play/' + game_url + '/clone/' + copy_token + '/' + parseInt(mouse_x) + '/' + parseInt(mouse_y));
				timeid = 0; // force full refresh next time
			}
		}
	} else {
		if (event.keyCode == 46) { // DEL
			if (select_id == copy_token) {
				copy_token = 0;
			}
			$.post('/play/' + game_url + '/delete/' + select_id);
				timeid = 0; // force full refresh next time
		}
	}
}

/// Event handle for (un)locking a token
function tokenLock() {
	if (mouse_over_id != 0) {
		var token = tokens[mouse_over_id];
		token.locked = !token.locked;
		
		// mark token as changed
		if (!change_cache.includes(mouse_over_id)) {
			change_cache.push(mouse_over_id);
		}
	}
}

/// Event handle for stretching a token to fit the screen
function tokenStretch() {
	if (mouse_over_id != 0) {
		var token = tokens[mouse_over_id];
		
		if (token.locked) {
			// ignore if locked
			console.log('cannot stretch locked token');
			return;
		}
		
		// stretch token to entire canvas (on deepest z-order)
		var canvas = $('#battlemap');
		token.size = -1;
		token.locked = true;
		token.zorder = min_z;
		min_z -= 1;
		
		// client-side prediction for position
		token.posx = canvas[0].width / 2;
		token.posy = canvas[0].height / 2;
			
		// mark token as changed
		if (!change_cache.includes(mouse_over_id)) {
			change_cache.push(mouse_over_id);
		}
	}
}

/// Event handle for moving token to lowest z-order
function tokenBottom() {
	if (mouse_over_id != 0) {
		var token = tokens[mouse_over_id];
		
		if (token.locked) {
			// ignore if locked
			console.log('cannot move locked token to bottom');
			return;
		}
		// move beneath lowest known z-order
		if (token.locked) {
			token.zorder = 1;
		} else {
			token.zorder = min_z - 1;
			--min_z;
		}
		
		// mark token as changed
		if (!change_cache.includes(mouse_over_id)) {
			change_cache.push(mouse_over_id);
		}
	}
}

/// Event handle for moving token to hightest z-order
function tokenTop() {
	if (mouse_over_id != 0) {
		var token = tokens[mouse_over_id];
		
		if (token.locked) {
			// ignore if locked
			console.log('cannot move locked token to top');
			return;
		}
		// move above highest known z-order
		if (token.locked) {
			token.zorder = -1;
		} else {
			token.zorder = max_z - 1;
			++max_z;
		}
			
		// mark token as changed
		if (!change_cache.includes(mouse_over_id)) {
			change_cache.push(mouse_over_id);
		}
	}
}


// --- GM stuff ---------------------------------------------------------------

// not used atm
function copyUrl(server, game_url) {
	var tmp = $('<input>');
	$('body').append(tmp);
	tmp.val('http://' + server + '/play/' + game_url).select();
	document.execCommand('copy');
	tmp.remove();
}

function toggleDropdown() {
	var scenes = $('#preview');
	if (scenes.css('display') == 'block') {
		scenes.css('display', 'none');
		setCookie('dropdown', 'hide');
	} else {
		scenes.css('display', 'block');
		setCookie('dropdown', 'show');
	}
}

function closeDropdown() {
	var scenes = $('#preview');
	scenes.css('display', 'none');
}

function addScene() {
	$.post(
		url='/gm/' + game_url + '/create',
		success=function(data) {
			location.reload();
		}
	);
}

function activateScene(scene_id) {
	$.post(
		url='/gm/' + game_url + '/activate/' + scene_id,
		success=function(data) {
			location.reload();
		}
	);
}
function cloneScene(scene_id) {
	$.post(
		url='/gm/' + game_url + '/clone/' + scene_id,
		success=function(data) {
			location.reload();
		}
	);
}
function deleteScene(scene_id) {
	$.post(
		url='/gm/' + game_url + '/delete/' + scene_id,
		success=function(data) {
			location.reload();
		}
	);
}

