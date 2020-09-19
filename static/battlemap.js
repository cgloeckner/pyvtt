
// --- image handling implementation ------------------------------------------

var images = [];
var canvas_ratio = 1.0; // canvas aspect ratio

/// Will clear the canvas
function clearCanvas() {
	var canvas = $('#battlemap');
	var context = canvas[0].getContext("2d");
	context.clearRect(0, 0, canvas[0].width, canvas[0].height);
	
	// Recalculate aspect ratio
	canvas_ratio = canvas[0].width / canvas[0].height;
}

var mem_canvas = null;

/// Get image pixel data
function getPixelData(token, x, y) {
	// note: tokens are drawn centered
	// x, y is relative to the token position
	
	var dom_canvas = $('#battlemap')[0];
	
	// setup in-memory canvas
	mem_canvas = document.createElement('canvas');
	mem_canvas.width  = token.size;
	mem_canvas.height = token.size;

	// query clean context
	var mem_ctx = mem_canvas.getContext('2d');
	mem_ctx.clearRect(0, 0, token.size, token.size);
	
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
		if (ratio >= canvas_ratio) {
			// most common case: image is wider than canvas (or same ratio)
			// needs to be stretched to fit width
			w = maxw
			h = w / ratio;
		} else {
			// image is taller than canvas
			// needs to be stretched to fit height
			h = maxh
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
	var min_x = token.posx - token.size / 2;
	var max_x = token.posx + token.size / 2;
	var min_y = token.posy - token.size / 2;
	var max_y = token.posy + token.size / 2;
	var in_box = min_x <= x && x <= max_x && min_y <= y && y <= max_y;
	if (!in_box) {
		return false;
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
	var background = null;
	// search for any fitting token with highest z-order (unlocked first)
	$.each(culling, function(index, item) {
		if (item != null && item.size == -1) {
			background = item;
		}
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
	if (result == null) {
		// fallback: grab background if possible
		result = background;
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
		tokens[data.id].posx = canvas[0].width / 2;
		tokens[data.id].posy = canvas[0].height / 2;
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
	
	// draw image
	context.save();
	context.translate(token.posx, token.posy);
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
	return document.cookie.split(key + '=')[1].split('; ')[0];
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
				container += '<a href="/play/' + game_title + '/logout" title="Logout">' + name + '</a>';
			} else {
				container += name;
			}
			container += '</span>';
			$('#players').append(container);
		}
	});
	
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
	target.innerHTML += '<div class="' + div_class + '"><img src="/static/d' + sides + '.png" style="filter: drop-shadow(1px 1px 10px ' + color + ') drop-shadow(-1px -1px 0 ' + color + ');"/><span class="result" style="color: ' + color + ';">' + result + '</span><span class="player">' + player + '<br />' + time + '</span></div>';
}

function updateRolls(rolls) {
	// show rolls
	var rolls_div = $('#rollbox')[0];
	rolls_div.innerHTML = '';
	$.each(rolls, function(index, roll) {
		showRoll(roll['sides'], roll['result'], roll['player'], roll['color'], roll['time']);
	});		
}


// --- game state implementation ----------------------------------------------

var game_title = '';
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
		url:  '/play/' + game_title + '/update',
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
			
			$('#error').css('visibility', 'hidden');
		}, error: function(jqXHR, text, error) {
		/*
			// animate 'Connecting' with multiple dots
			var error = $('#error');
			error.css('visibility', 'visible');
			var dots = error[0].innerHTML.split('Connecting')[1].length;
			error[0].innerHTML = 'Connecting';
			dots = (dots + 1) % 10;
			for (i = 1; i <= dots; ++i) {
				error[0].innerHTML += '.';
			}
		*/
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
function start(title) {
	game_title = title;
	
	// notify game about this player
	navigator.sendBeacon('/play/' + game_title + '/join');
	
	updateGame();
}

/// Handles disconnecting
function disconnect() {
	// note: only works if another tab stays open
	navigator.sendBeacon('/play/' + game_title + '/disconnect');
}

function uploadDrag(event) {
	event.preventDefault();
	
	mouse_x = event.offsetX;
	mouse_y = event.offsetY;
}

function uploadDrop(event) {
	event.preventDefault();

	var queue = $('#uploadqueue')[0];
	queue.files = event.dataTransfer.files;
	
	var f = new FormData($('#uploadform')[0]);
	
	$.ajax({
		url: '/play/' + game_title + '/upload/' + mouse_x + '/' + mouse_y,
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

function updateTokenbar() {
	$('#tokenbar').css('visibility', 'hidden');

	// query mouse over token
	var token = selectToken(mouse_x, mouse_y);
	if (token != null) {
		mouse_over_id = token.id;
		
		if (!grabbed) {
			// update tokenbar if not grabbed
			$('#tokenbar').css('visibility', 'visible');
			
			// adjust position based on size and aspect ratio
			var canvas = $('#battlemap');
			var bx = canvas[0].getBoundingClientRect();
			
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
			var size = token.size;
			if (size == -1) {
				if (ratio >= canvas_ratio) {
					// most common case: image is wider than canvas (or same ratio)
					// needs to be stretched to fit width
					size = canvas[0].width
				} else {
					// image is taller than canvas
					// needs to be stretched to fit height
					size = canvas[0].height * ratio;
				}
			}
			
			// setup position
			var x = bx.left + token.posx - size / 3 + 5;
			var y = bx.top + token.posy - 36;
			
			$('#tokenbar').css('left', x + 'px');
			$('#tokenbar').css('top', y + 'px');
			
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
		}
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
}

/// Event handle for start grabbing a token
function tokenGrab(event) {
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
			token.size   = 64;
			
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
			if (token.size > 1440) {
				token.size = 1440;
			}
			if (token.size < 32) {
				token.size = 32;
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
	$.post('/play/' + game_title + '/roll/' + sides);
}

/// Event handle shortcuts on tokens
function tokenShortcut(event) {
	if (event.ctrlKey) {
		if (event.keyCode == 67) { // CTRL+C
			copy_token = select_id;
		} else if (event.keyCode == 86) { // CTRL+V
			if (copy_token > 0) {
				$.post('/play/' + game_title + '/clone/' + copy_token + '/' + parseInt(mouse_x) + '/' + parseInt(mouse_y));
				timeid = 0; // force full refresh next time
			}
		}
	} else {
		if (event.keyCode == 46) { // DEL
			if (select_id == copy_token) {
				copy_token = 0;
			}
			$.post('/play/' + game_title + '/delete/' + select_id);
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
		token.rotate = 0;
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

