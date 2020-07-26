
// --- image handling implementation ------------------------------------------

var images = [];

/// Will clear the canvas
function clearCanvas() {
	var canvas = $('#battlemap');
	var context = canvas[0].getContext("2d");
	context.clearRect(0, 0, canvas[0].width, canvas[0].height);
	
	// draw separation line for GM-area
	context.beginPath();
	context.moveTo(1001, 0);
	context.lineTo(1001, canvas[0].height);
	context.stroke();
}

// --- token implementation ---------------------------------------------------

var tokens       = []; // holds all tokens, updated by the server
var change_cache = []; // holds ids of all client-changed tokens

/// Token constructor
function Token(id, url) {
	this.id = id;
	this.posx = 0;
	this.posy = 0;
	this.size = 250;
	this.url = url;
	this.rotate = 0.0;
	this.locked = false;
}

/// Add token with id and url to the scene
function addToken(id, url) {
	tokens[id] = new Token(id, url);
}

/// Determines which token is selected when clicking the given position
function selectToken(x, y) {
	var result = null;
	// search for any fitting (unlocked) token
	$.each(tokens, function(index, item) {
		if (item != null && !item.locked) {
			var min_x = item.posx - item.size / 2;
			var max_x = item.posx + item.size / 2;
			var min_y = item.posy - item.size / 2;
			var max_y = item.posy + item.size / 2;
			if (min_x <= x && x <= max_x && min_y <= y && y <= max_y) {
				result = item;
			}
		}
	});
	if (result == null) {
		// search for any fitting (locked) token
		$.each(tokens, function(index, item) {
			if (item != null && item.locked) {
				var min_x = item.posx - item.size / 2;
				var max_x = item.posx + item.size / 2;
				var min_y = item.posy - item.size / 2;
				var max_y = item.posy + item.size / 2;
				if (min_x <= x && x <= max_x && min_y <= y && y <= max_y) {
					result = item;
				}
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
	tokens[data.id].size   = data.size;
	tokens[data.id].rotate = data.rotate;
	tokens[data.id].locked = data.locked;
}

/// Draws a single token (show_ui will show the selection box around it)
function drawToken(token, show_ui) {
	// cache image if necessary
	if (!images.includes(token.url)) {
		images[token.url] = new Image();
		images[token.url].src = token.url;
	}
	
	// calculate new height (keeping aspect ratio)
	var ratio  = images[token.url].height / images[token.url].width;
	var w = token.size;
	var h = w * ratio;
	
	// draw image
	var canvas = $('#battlemap');
	var context = canvas[0].getContext("2d");
	context.save();
	context.translate(token.posx, token.posy);
	if (show_ui) {
		context.beginPath();
		context.moveTo(-w/2, -h/2);
		context.lineTo(w/2, -h/2);
		context.lineTo(w/2, h/2);
		context.lineTo(-w/2, h/2);
		context.lineTo(-w/2, -h/2);
		context.stroke();
	}
	context.rotate(token.rotate * 3.14/180.0);
	context.drawImage(images[token.url], -w / 2, -h / 2, w, h);
	context.restore();
}

// --- game state implementation ----------------------------------------------

var game_title = '';
var timeid = 0;

var mouse_x = 0;
var mouse_y = 0;

var select_id = 0; // determines selected token
var grabbed = 0; // determines whether grabbed or not
var update_tick = 0; // delays updates to not every loop tick

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
			'size'  : t.size,
			'rotate': t.rotate,
			'locked': t.locked
		};
		changes.push(data);
	});
	change_cache = [];
	
	// start update with server
	$.ajax({
		type: 'POST',
		url:  '/play/' + game_title + '/update',
		dataType: 'json',
		data: {
			'timeid'  : 0,
			'changes' : JSON.stringify(changes)
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
				
			// show rolls
			$.each(response['rolls'], function(index, info) {
				$('#rolls')[0].append(info + '\n');
			});
		}
	});
}

/// Draw the entire scene (locked tokens in the background, unlocked in foreground)
function drawScene() {
	clearCanvas();
	
	// draw locked tokens
	$.each(tokens, function(index, token) {
		if (token != null && token.locked) {
			drawToken(token, token.id == select_id);
		}
	});
	
	// draw unlocked tokens
	$.each(tokens, function(index, token) {
		if (token != null && !token.locked) {
			drawToken(token, token.id == select_id);
		}
	});
}

/// Updates the entire game: update tokens from time to time, drawing each time
function updateGame() {
	if (update_tick < 0) {
		console.log('update');
		updateTokens();
		update_tick = 500.0 / (1000.0 / fps);
	} else {
		update_tick -= 1;
	}
	
	drawScene();
	setTimeout("updateGame()", 1000.0 / fps);
}

/// Sets up the game and triggers the update loop
function start(title) {
	game_title = title;
	
	updateGame();
}

// ----------------------------------------------------------------------------

/// Event handle for start grabbing a token
function tokenGrab() {
	mouse_x = event.offsetX;
	mouse_y = event.offsetY;
	
	prev_id = select_id;
	
	select_id = 0;
	var token = selectToken(mouse_x, mouse_y);
	if (token != null) {
		select_id = token.id;
		grabbed = true;
		
		// show GM-info
		$('#info')[0].innerHTML = 'Token#' + select_id + ' at (' + token.posx + '|' + token.posy + ')';
		$('#locked')[0].checked = token.locked;
	}
}

/// Event handle for releasing a grabbed token
function tokenRelease() {
	if (select_id != 0) {
		grabbed = false;
	}
}

/// Event handle for moving a grabbed token (if not locked)
function tokenMove() {
	mouse_x = event.offsetX;
	mouse_y = event.offsetY;
	
	if (select_id != 0 && grabbed) {
		var token = tokens[select_id];
		if (token == null || token.locked) {
			return;
		}
		
		// update position
		token.posx = mouse_x;
		token.posy = mouse_y;
		
		// show GM-info
		var token = tokens[select_id];
		$('#info')[0].innerHTML = 'Token#' + select_id + ' at (' + token.posx + '|' + token.posy + ')';
		
		// mark token as changed
		if (!change_cache.includes(select_id)) {
			change_cache.push(select_id);
		}
	}
	
	$('#info')[0].innerHTML = 'Mouse (' + mouse_x + '|' + mouse_y + ')';
}

/// Event handle for rotation and scaling of tokens (if not locked)
function tokenWheel(event) {
	if (select_id != 0) {
		var token = tokens[select_id];
		if (token.locked) {
			return;
		}

		if (event.shiftKey) {
			// handle rotation
			token.rotate = token.rotate - 5 * event.deltaY;
			if (token.rotate >= 360.0 || token.rotate <= -360.0) {
				token.rotate = 0.0;
			}
			
			// mark token as changed
			if (!change_cache.includes(select_id)) {
				change_cache.push(select_id);
			}
			
		} else if (event.altKey) {
			// handle scaling
			token.size = token.size - 5 * event.deltaY;
			if (token.size > 1440) {
				token.size = 1440;
			}
			if (token.size < 16) {
				token.size = 16;
			}
			
			// mark token as changed
			if (!change_cache.includes(select_id)) {
				change_cache.push(select_id);
			}
		}
	}
}

/// GM Event handle for (un)locking a token
function tokenLock() {
	if (select_id != 0) {
		tokens[select_id].locked = $('#locked')[0].checked;
		
		// mark token as changed
		if (!change_cache.includes(select_id)) {
			change_cache.push(select_id);
		}
	}
}

/// GM Event handle for stretching a token to fit the screen
function tokenStretch() {
	if (select_id != 0) {
		var token = tokens[select_id];
		
		// stretch and center token in the center
		token.posx   = 500;
		token.posy   = 360;
		token.size   = 1000;
		token.rotate = 0;
		token.locked = true;
			
		// mark token as changed
		if (!change_cache.includes(select_id)) {
			change_cache.push(select_id);
		}
	}
}

/// GM Event handle to clone a token
function tokenClone() {
	$.post('/gm/' + game_title + '/clone/' + select_id);
}

/// GM Event handle to delete a token
function tokenDelete() {
	$.post('/gm/' + game_title + '/delete/' + select_id);
}

/// GM Event handle to clear all tokens in the playing area
function clearVisible() {
	$.post('/gm/' + game_title + '/clear_tokens');
}


// TODO: reimplement later

function rollDice(sides) {
	$.post('/play/' + game_title + '/roll/SHITFACE/' + sides);
}

function clearRolls() {
	$.post('/gm/' + game_title + '/clear_rolls');
	$('#rolls')[0].innerHTML = '';
}


