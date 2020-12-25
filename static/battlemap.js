
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
	mem_canvas.width  = w;
	mem_canvas.height = h;
	
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
	
	// clear memory canvas
	var mem_ctx = mem_canvas.getContext('2d');
	mem_ctx.clearRect(0, 0, mem_canvas.width, mem_canvas.height);
	
	var dom_canvas = $('#battlemap')[0];
	var sizes = getActualSize(token, dom_canvas.width, dom_canvas.height);
	
	// draw image
	mem_ctx.save();
	mem_ctx.translate(dom_canvas.width / 2, dom_canvas.height / 2);
	if (token.flipx) {
		mem_ctx.scale(-1, 1);
		mem_ctx.rotate(token.rotate * -3.14/180.0);
	} else {
		mem_ctx.rotate(token.rotate * 3.14/180.0);
	}
	
	mem_ctx.drawImage(images[token.url], -sizes[0] / 2, -sizes[1] / 2, sizes[0], sizes[1]);
	
	mem_ctx.restore();
	
	// query pixel data
	// note: consider (x,y) is relative to token's center
	return mem_ctx.getImageData(x + dom_canvas.width / 2, y + dom_canvas.height / 2, 1, 1).data;
}

// --- token implementation ---------------------------------------------------

var tokens         = []; // holds all tokens, updated by the server
var tokens_added   = []; // holds token id => opacity when recently added
var tokens_removed = []; // holds token id => (token, opacity) when recently removed
var change_cache   = []; // holds ids of all client-changed tokens

var player_selections = []; // buffer that contains selected tokens and corresponding player colors
var allow_multiselect = false; // whether client is allowed to select multiple tokens

var culling = []; // holds tokens for culling
var min_z = -1; // lowest known z-order
var max_z =  1; // highest known z-order
var min_token_size = 50;

/// Token constructor
function Token(id, url) {
	this.id = id;
	this.posx = 0;
	this.posy = 0;
	this.zorder = 0;
	this.size = 250;
	this.url = url;
	this.rotate = 0.0;
	this.flipx = false;
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
	var ratio = src_h / src_w;
	
	// Basic Concept: r = h/w  <==>  h = w*r  <==>  w = h/r
	
	// scale token via width (most common usecase)
	var h = 0;
	var w = 0;
	if (token.size > -1) {
		if (src_h > src_w) {
			// scale token via height
			h = token.size;
			w = h / ratio;
		} else {
			// scale token via width
			w = token.size;
			h = w * ratio;
		}
	} else {
		if (ratio > 0.56) {
			// resize to canvas height
			h = maxh / canvas_scale;
			w = h / ratio;
		} else {
			// resize to canvas width
			w = maxw / canvas_scale;
			h = w * ratio;
		}
	}
	
	return [w, h];
}

/// Determiens if position is within token's bounding box
function isOverToken(x, y, token) {
	var canvas   = $('#battlemap');
	var size     = getActualSize(token, canvas[0].width, canvas[0].height);
	var max_size = Math.max(size[0], size[1]); // because the token might be rotated
	
	// 1st stage: bounding box test
	if (token.size > 0) {
		var min_x = token.posx - max_size / 2;
		var max_x = token.posx + max_size / 2;
		var min_y = token.posy - max_size / 2;
		var max_y = token.posy + max_size / 2;
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
	tokens[data.id].flipx  = data.flipx;
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
	
	// handle position and scale
	context.save();
	context.translate(token.posx * canvas_scale, token.posy * canvas_scale);
	
	// handle token spawn
	if (tokens_added[token.id] != null) {
		var value = tokens_added[token.id];
		context.globalAlpha = value;
		context.scale(5 - 4 * value, 5 - 4 * value);
		value += 0.075;
		if (value < 1.0) {
			tokens_added[token.id] = value;
		} else {
			delete tokens_added[token.id];
		}
	}
	
	// handle token despawn
	if (tokens_removed[token.id] != null) {
		var value = tokens_removed[token.id][1];
		context.globalAlpha = value;
		context.scale(5 - 4 * value, 5 - 4 * value);
		value -= 0.075;
		if (value > 0.0) {
			tokens_removed[token.id][1] = value;
		} else {
			delete tokens_removed[token.id];
		}
	}
	
	// handle fip, rotation
	if (token.flipx) {
		context.scale(-1, 1);
		context.rotate(token.rotate * -3.14/180.0);
	} else {
		context.rotate(token.rotate * 3.14/180.0);
	}
	
	// handle selection
	if (color != null) {
		context.shadowColor = color;
		context.shadowBlur = 25;
	}
		
	// draw image
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
			$('#players').append('<span id="player_' + name + '" class="player" style="filter: drop-shadow(1px 1px 9px ' + color + ') drop-shadow(-1px -1px 0 ' + color + ');">' + name + '</span>');
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

var rolls        = []; // current rolls
var roll_timeout = 10000.0; // ms until roll will diappear

/// Roll constructor
function Roll(sides, playername, result) {
	this.sides      = sides;
	this.playername = player;
	this.result     = result;
}

function addRoll(sides, result, color, id) {
	// create dice result
	var container = $('#d' + sides + 'box');
	css = 'filter: drop-shadow(1px 1px 5px ' + color + ') drop-shadow(-1px -1px 0 ' + color + ');';
	var span = '<span id="roll_id_' + id + '" style="' + css + '">' + result + '</span>';
	container.prepend(span);
	
	// prepare automatic cleanup
	var dom_span = container.children(':first-child')
	if (result == 1 || result == sides) {
		dom_span.addClass('natroll');
	}
	dom_span.delay(roll_timeout).fadeOut(5000, function() { this.remove(); });
}

function updateRolls(rolls) {
	$.each(rolls, function(index, roll) {
		addRoll(roll['sides'], roll['result'], roll['color'], roll['id']);
	});                      
}

// --- game state implementation ----------------------------------------------

var game_url = '';
var gm_name = '';
var dropdown = false;
var timeid = 0;
var full_update = true;
var scene_id = 0;

var mouse_x = 0; // relative to canvas
var mouse_y = 0;

var copy_token = 0; // determines copy-selected token (CTRL+C)
var select_ids = []; // contains selected tokens' ids
var primary_id = 0; // used to specify "leader" in group (for relative movement)
var mouse_over_id = 0; // determines which token would be selected
var grabbed = 0; // determines whether grabbed or not
var update_tick = 0; // delays updates to not every loop tick
var full_tick = 0; // counts updates until the next full update is requested

var select_from_x = null;
var select_from_y = null;

var fps = 60;
var update_cycles = 30;

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
			'flipx' : t.flipx,
			'locked': t.locked
		};
		changes.push(data);
	});
	
	if (full_tick == 0) {
		full_update = true;
		full_tick = 1;
	} else {
		full_tick -= 1;
	}
	
	// start update with server
	$.ajax({
		type: 'POST',
		url:  '/' + gm_name + '/' + game_url + '/update',
		dataType: 'json',
		data: {
			'timeid'      : timeid,
			'full_update' : full_update,
			'changes'     : JSON.stringify(changes),
			'selected'    : JSON.stringify(select_ids),
			'scene_id'    : scene_id
		},
		success: function(response) {
			var switch_scene = false;
			
			// update current timeid
			timeid = response['timeid'];
			if (scene_id != response['scene_id']) {
				scene_id = response['scene_id'];
				full_update = true;
				switch_scene = true;
			}
			   
			if (!switch_scene) {        
				// search added tokens
				$.each(response['tokens'], function(index, token) {
					if (!(token.id in tokens)) {
						tokens_added[token.id] = 0.0;
					}
				});
			}
			
			// clear all local tokens if a full update was received
			if (full_update) {
				console.log('Received full update');
				
				if (!switch_scene) {
					// search deleted tokens
					var all_ids = [];
					$.each(response['tokens'], function(index, token) {
						all_ids.push(token.id);
					});
					$.each(tokens, function(index, token) {
						if (token != null && !(all_ids.includes(token.id))) {
							// token got deleted
							tokens_removed[token.id] = [token, 1.0];
						}
					});
				}
				
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
			
			full_update = false;
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
		drawToken(background, select_ids.includes(background.id));
	}
	$.each(culling, function(index, token) {
		var color = null;
		$.each(player_selections, function(index, arr) {
			$.each(JSON.parse(arr[0]), function(ind, id) {
				if (id == token.id) {
					color = arr[1];
				}
			});
		});
		if (color == null && select_ids.includes(token.id)) {
			color = getCookie('playercolor');
		}
		drawToken(token, color);
	});
	// draw recently removed tokens (animated)
	$.each(tokens_removed, function(index, token) {
		if (tokens_removed[index] != null) {
			drawToken(tokens_removed[index][0]);
		}
	});
	
	// reverse culling for top-to-bottom token searching
	culling.reverse();
	
	if (select_from_x != null) {
		// draw selection box
		var canvas = $('#battlemap');
		var context = canvas[0].getContext("2d");
		var select_width  = mouse_x - select_from_x;
		var select_height = mouse_y - select_from_y;
		context.beginPath();
		context.rect(select_from_x * canvas_scale, select_from_y * canvas_scale, select_width * canvas_scale, select_height * canvas_scale);
		context.strokeStyle = "#070707";
		context.fillStyle = "rgba(255, 255, 255, 0.25)"; 
		context.fillRect(select_from_x * canvas_scale, select_from_y * canvas_scale, select_width * canvas_scale, select_height * canvas_scale);
		context.stroke();
	}
}

/// Updates the entire game: update tokens from time to time, drawing each time
function updateGame() {
	if (update_tick < 0) {
		updateTokens();
		update_tick = update_cycles;
	} else {
		update_tick -= 1;
	}
	
	drawScene();
	setTimeout("updateGame()", 1000.0 / fps);
}

/// Handles login and triggers the game
function login(url, name) {
	var playername  = $('#playername').val();
	var playercolor = $('#playercolor').val();
	
	$.ajax({
		type: 'POST',
		url:  '/' + name + '/' + url + '/login',
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
				
				// start game
				start(url, name);
			}
		}
	});
}

/// Sets up the game and triggers the update loop
function start(url, name) {	
	// setup in-memory canvas (for transparency checking)
	mem_canvas = document.createElement('canvas');
	
	// disable window context menu for token right click
	document.addEventListener('contextmenu', event => {
	  event.preventDefault();
	});
	
	// drop zone implementation (using canvas) --> also as players :) 
	battlemap.addEventListener('dragover', mouseDrag);
	battlemap.addEventListener('drop', uploadDrop);

	// desktop controls
	battlemap.addEventListener('mousedown', tokenGrab);
	battlemap.addEventListener('mousemove', tokenMove);
	battlemap.addEventListener('mouseup', tokenRelease);
	battlemap.addEventListener('wheel', tokenWheel);
	document.addEventListener('keydown', tokenShortcut);

	// mobile control fix
	battlemap.addEventListener('touchstart', tokenGrab);
	battlemap.addEventListener('touchmove', tokenMove);
	battlemap.addEventListener('touchend', tokenRelease);
	
	// setup game
	game_url = url;
	gm_name = name;
	
	// notify game about this player
	navigator.sendBeacon('/' + gm_name + '/' + game_url + '/join');
	
	$(window).on('unload', function() {
		disconnect();
	});
	
	updateGame();
}

/// Handles disconnecting
function disconnect() {
	// note: only works if another tab stays open
	navigator.sendBeacon('/' + gm_name + '/' + game_url + '/disconnect');
}

var last_scale = 1.0;

function mouseDrag(event) {
	event.preventDefault();
	pickCanvasPos(event);
	
	if (primary_id != 0) {
		var first_token = tokens[primary_id] 
		var dx = first_token.posx - mouse_x;
		var dy = first_token.posy - mouse_y;
		var scale = Math.sqrt(dx*dx + dy*dy);
		
		if (drag_action == 'resize') {
			var ratio = 1.0;
			if (scale > last_scale) {
				ratio = 1.1;
			}
			if (scale < last_scale) {
				ratio = 0.95;
			}
			last_scale = scale;
			
			// resize all selected tokens
			$.each(select_ids, function(index, id) {
				var token = tokens[id];
				if (token.locked) {
					return;
				}
				
				token.size = Math.round(token.size * ratio);
				if (token.size > min_token_size * 10) {
					token.size = min_token_size * 10;
				}
				if (token.size < min_token_size) {
					token.size = min_token_size;
				}
				
				// mark token as changed
				if (!change_cache.includes(id)) {
					change_cache.push(id);
				}
			});
			
		} else if (drag_action == 'rotate') {
			var delta = -10.0;
			var rot_val = dx;
			if (Math.abs(dy) > Math.abs(dx)) {
				rot_val = dy;
			}
			if (rot_val == last_scale) {
				delta = 0.0;
			}
			if (rot_val < last_scale) {
				delta = -delta;
			}
			last_scale = rot_val;
			
			// rotate all selected tokens
			$.each(select_ids, function(index, id) {
				var token = tokens[id];
				if (token.locked) {
					return;
				}
				
				token.rotate += delta;
				
				// mark token as changed
				if (!change_cache.includes(id)) {
					change_cache.push(id);
				}
			});
		}
	}
	
	updateTokenbar();
}

function uploadDrop(event) {
	event.preventDefault();
	pickCanvasPos(event);
	
	var queue = $('#uploadqueue')[0];
	queue.files = event.dataTransfer.files;
	
	var f = new FormData($('#uploadform')[0]);
	
	$.ajax({
		url: '/' + gm_name + '/' + game_url + '/upload/' + mouse_x + '/' + mouse_y,
		type: 'POST',
		data: f,
		contentType: false,
		cache: false,
		processData: false,
		success: function(response) {
			// reset uploadqueue
			$('#uploadqueue').val("");
		}
	});
}

function showTokenbar(token_id) {
	if (select_ids.includes(token_id)) {
		$('#tokenbar').css('visibility', 'visible');
	} else {
		$('#tokenbar').css('visibility', 'hidden');
	}
}

var token_icons = ['Rotate', 'Top', 'Bottom', 'Resize', 'FlipX', 'Lock'];

function updateTokenbar() {
	$('#tokenbar').css('visibility', 'hidden');

	if (primary_id && !grabbed) {
		token = tokens[primary_id];
		
		if (token == null) {
			return;
		}
		
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
		
		$('#tokenbar').css('left', bx.left + 'px');
		$('#tokenbar').css('top',  bx.top  + 'px');
		$('#tokenbar').css('visibility', '');
		
		$.each(token_icons, function(index, name) {
			// calculate position based on angle
			var degree = 360.0 / token_icons.length;
			var s = Math.sin((-90.0 + index * degree) * 3.14 / 180);
			var c = Math.cos((-90.0 + index * degree) * 3.14 / 180);
			
			var x = size * c * 0.8 + token.posx * canvas_scale - 12;
			var y = size * s * 0.8 + token.posy * canvas_scale - 12;
			
			// force position to be on the screen
			x = Math.max(0, Math.min(canvas.width(), x));
			y = Math.max(0, Math.min(canvas.height(), y));
			
			// place icon
			$('#token' + name).css('left', x + 'px');
			$('#token' + name).css('top',  y + 'px');
		});
		
		// handle locked mode
		if (token.locked) {
			$('#tokenFlipX').css('visibility', 'hidden');
			$('#tokenLock')[0].src = '/static/locked.png';
			$('#tokenTop').css('visibility', 'hidden');
			$('#tokenBottom').css('visibility', 'hidden');
			$('#tokenResize').css('visibility', 'hidden');
			$('#tokenRotate').css('visibility', 'hidden');
		} else {
			$('#tokenFlipX').css('visibility', '');
			$('#tokenLock')[0].src = '/static/unlocked.png';
			$('#tokenTop').css('visibility', '');
			$('#tokenBottom').css('visibility', '');
			$('#tokenResize').css('visibility', '');    
			$('#tokenRotate').css('visibility', '');
		}
	}
}

// ----------------------------------------------------------------------------

var drag_action = ''; // used to identify dragging for resize or rotate

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
	
	if (event.buttons == 1) {
		// Left Click: select token
		var token = selectToken(mouse_x, mouse_y);
		
		if (token != null) {
			// reselect only if token wasn't selected before
			if (!select_ids.includes(token.id)) {
				select_ids = [token.id];
				primary_id = token.id;
			} else {
				primary_id = token.id;
			}
			grabbed = true;
		} else {
			// Clear selection
			select_ids = [];
			primary_id = 0;
			
			// start selection box
			select_from_x = mouse_x;
			select_from_y = mouse_y;
		}
	
	} else if (event.buttons == 2) {
		// Right click: reset token scale & rotation
		$.each(select_ids, function(index, id) {
			var token = tokens[id];
			
			token.rotate = 0;
			token.size   = Math.round(min_token_size * 1.5);
			
			if (!change_cache.includes(id)) {
				change_cache.push(id);
			}
		});
	
	}
}

/// Event handle for releasing a grabbed token
function tokenRelease() {
	if (select_ids.length > 0) {
		grabbed = false;
	}
	
	$('#battlemap').css('cursor', 'default');
	
	if (select_from_x != null) {
		// finish selection box
		var select_width  = mouse_x - select_from_x;
		var select_height = mouse_y - select_from_y;
		
		// handle box created to the left
		if (select_width < 0) {
			select_from_x = select_from_x + select_width;
			select_width *= -1;
		}
			 
		// handle box created to the top
		if (select_height < 0) {
			select_from_y = select_from_y + select_height;
			select_height *= -1;
		}
		
		// query tokens in range
		$.ajax({
			url: '/' + gm_name + '/' + game_url + '/range_query/' + select_from_x + '/' + select_from_y + '/' + select_width + '/' + select_height,
			type: 'GET',
			success: function(response) {
				select_ids = JSON.parse(response);
				// pick primary token
				if (select_ids.length > 0) {
					primary_id = select_ids[0];
				} else {
					primary_id = 0;
				}
			}
		});
	}
	
	select_from_x = null;
	select_from_y = null;
	
	updateTokenbar();
}

/// Event handle for moving a grabbed token (if not locked)
function tokenMove(event) {
	pickCanvasPos(event);
	
	if (primary_id != 0 && grabbed) {
		var token = tokens[primary_id];
		 
		// transform cursor
		if (token == null) {
			$('#battlemap').css('cursor', 'default');
		} else if (token.locked) {
			$('#battlemap').css('cursor', 'not-allowed');
		} else {                                         
			$('#battlemap').css('cursor', 'grab');
		}
		
		if (token != null && !token.locked) {
			var prev_posx = token.posx;
			var prev_posy = token.posy;
			
			$.each(select_ids, function(index, id) {
				var t = tokens[id];
				if (!t.locked) {
					// get position relative to primary token
					var dx = t.posx - prev_posx;
					var dy = t.posy - prev_posy;
					// move relative to primary token
					t.posx = mouse_x + dx;
					t.posy = mouse_y + dy;
					
					// mark tokens as changed
					if (!change_cache.includes(t.id)) {
						change_cache.push(t.id);
					}
				}
			});
		}
	} else {
		var token = selectToken(mouse_x, mouse_y);
		 
		// transform cursor
		if (token == null) {
			$('#battlemap').css('cursor', 'default');
		} else if (token.locked) {
			$('#battlemap').css('cursor', 'not-allowed');
		} else {                                         
			$('#battlemap').css('cursor', 'grab');
		}
	}
	
	updateTokenbar();
}

/// Event handle for rotation via mouse wheel
function tokenWheel(event) {
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		if (token.locked) {
			return;
		}

		// handle rotation
		token.rotate = token.rotate - 5 * event.deltaY;
		if (token.rotate >= 360.0 || token.rotate <= -360.0) {
			token.rotate = 0.0;
		}
		
		// mark token as changed
		if (!change_cache.includes(id)) {
			change_cache.push(id);
		}
	});
	
	updateTokenbar();
}

/// Event handle to click a dice
function rollDice(sides) {
	$('#d' + sides).addClass('shake');
	$.post('/' + gm_name + '/' + game_url + '/roll/' + sides);
	setTimeout(function() {	$('#d' + sides).removeClass('shake'); }, 500);
}

/// Event handle shortcuts on (first) selected token
function tokenShortcut(event) {
	if (event.ctrlKey) {
		if (event.keyCode == 67) { // CTRL+C
			copy_token = select_ids[0];
		} else if (event.keyCode == 86) { // CTRL+V
			if (copy_token > 0) {
				$.post('/' + gm_name + '/' + game_url + '/clone/' + copy_token + '/' + parseInt(mouse_x) + '/' + parseInt(mouse_y));
				full_update = true; // force full refresh next time
			}
		}
	} else {
		if (event.keyCode == 46) { // DEL
			if (select_ids[0] == copy_token) {
				copy_token = 0;
			}
			$.post('/' + gm_name + '/' + game_url + '/delete/' + select_ids[0]);
				full_update = true; // force full refresh next time
		}
	}
}

/// Event handle for fliping a token x-wise
function tokenFlipX() {
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		
		if (token.locked) {
			// ignore if locked
			console.log('cannot flip locked token');
			return; 
		}
		token.flipx = !token.flipx;
		
		// mark token as changed
		if (!change_cache.includes(id)) {
			change_cache.push(id);
		}
	});
}

/// Event handle for (un)locking a token
function tokenLock() {
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		token.locked = !token.locked;
		
		// mark token as changed
		if (!change_cache.includes(id)) {
			change_cache.push(id);
		}
	});
}

/// Event handle for resize a token
function tokenResize() {
	drag_action = 'resize';
}

/// Event handle for rotating a token
function tokenRotate() {
	drag_action = 'rotate'; 
}

/// Event handle for quitting rotation/resize dragging
function tokenQuitAction() {
	drag_action = '';    
}

/// Event handle for moving token to lowest z-order
function tokenBottom() {
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		
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
		if (!change_cache.includes(id)) {
			change_cache.push(id);
		}
	});
}

/// Event handle for moving token to hightest z-order
function tokenTop() {
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		
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
		if (!change_cache.includes(id)) {
			change_cache.push(id);
		}
	});
}

// --- GM stuff ---------------------------------------------------------------

// not used atm
function copyUrl(server, game_url) {
	var tmp = $('<input>');
	$('body').append(tmp);
	tmp.val('http://' + server + '/' + gm_name + '/' + game_url).select();
	document.execCommand('copy');
	tmp.remove();
}

function openDropdown(force=false) {
	var scenes = $('#preview');
	var hint   = $('#drophint');
	if (force || !dropdown) {
		scenes.animate({
			top: "+=100"
		}, 500);
		hint.animate({
			top: "+=100"
		}, 500);
	}
	dropdown = true;
	hint.fadeOut(500, 0.0);
}

function closeDropdown(force=false) {
	var scenes = $('#preview'); 
	var hint   = $('#drophint');
	if (force || dropdown) {
		scenes.animate({
			top: "-=100"
		}, 500); 
		hint.animate({
			top: "-=100"
		}, 500);
	}
	dropdown = false;
	hint.fadeIn(500, 0.0);
}

function addScene() {
	$.post(
		url='/vtt/create-scene/' + game_url,
		success=function(data) {
			$('#preview')[0].innerHTML = data; 
			updateGame();
		}
	);
}

function activateScene(scene_id) {
	$.post(
		url='/vtt/activate-scene/' + game_url + '/' + scene_id,
		success=function(data) {       
			$('#preview')[0].innerHTML = data;
			updateGame();
		}
	);
}
function cloneScene(scene_id) {
	$.post(
		url='/vtt/clone-scene/' + game_url + '/' + scene_id,
		success=function(data) { 
			$('#preview')[0].innerHTML = data;
			updateGame();
		}
	);
}
function deleteScene(scene_id) {
	$.post(
		url='/vtt/delete-scene/' + game_url + '/' + scene_id,
		success=function(data) {
			$('#preview')[0].innerHTML = data;
			updateGame();
		}
	);
}


