/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/
  
var mouse_x = 0; // relative to canvas
var mouse_y = 0;

var copy_tokens   = [];    // determines copy-selected token (CTRL+C)
var select_ids    = [];    // contains selected tokens' ids
var primary_id    = 0;     // used to specify "leader" in group (for relative movement)
var mouse_over_id = 0;     // determines which token would be selected
var grabbed       = false; // determines whether grabbed or not

var select_from_x = null;
var select_from_y = null;

var dice_shake = 750; // ms for shaking animation

var zooming = true; // DEBUG switch for enabling the experimental feature

var drag_dice    = null;    // indicates which dice is dragged around (by number of sides)
var drag_players = null;    // indicates if players are dragged around
var over_player  = null;    // indicates over which player the mouse is located (by name)

var dice_snap = true;       // force dice to snap to borders

var default_dice_pos = {};  // default dice positions

function enableZooming() {
	zooming = $('#zooming').prop('checked');
}

// --- token implementation -------------------------------------------

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

// --- player implementation ------------------------------------------

var players = {};

/// Player constructor
function Player(name, uuid, color, ip, country, index) {
	this.name    = name;
	this.uuid    = uuid;
	this.color   = color;
	this.ip      = ip;
	this.country = country;
	this.index   = index;
	this.is_last = false;
}


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

function rebuildPlayers() {
	// build players array sorted by index
	var indices = {};
	$.each(players, function(uuid, p) {
		indices[p.index] = p;
	}),
	
	// rebuild players container
	$('#players')[0].innerHTML = '';
	$.each(indices, function(index, p) {
		showPlayer(p, true);
	});
}

function showPlayer(p, force=false) { 
	if (!force && p.uuid in players) {
		// ignore existing player
		return;
	}
	
	var flag = '';
	if (p.country != '?') {
		flag = '<img src="https://www.countryflags.io/' + p.country + '/flat/16.png" />';
	}
	
	// create player container (uuid as id, custom colored, optional kick click, draggable)
	var coloring = ' style="filter: drop-shadow(1px 1px 9px ' + p.color + ') drop-shadow(-1px -1px 0 ' + p.color + ');"';
	var ordering = ' onMouseEnter="onMouseOverPlayer(\'' + p.uuid + '\');"';
	   ordering += ' onMouseLeave="onMouseLeavePlayer(\'' + p.uuid + '\');"';
	
	// create player menu for this player
	var menu = '<div class="playermenu" id="playermenu_' + p.uuid + '">'
	if (p.index > 0) {
		menu += '<img src="/static/left.png" class="left" onClick="onPlayerOrder(-1);" />'
	}
	if (is_gm && p.uuid != my_uuid) {
		menu += '<img src="/static/kick.gif" class="center" onClick="kickPlayer(\'' + game_url + '\', \'' + p.uuid + '\');" />';
	}
	if (!p.is_last) {
		menu += '<img src="/static/right.png" class="right" onClick="onPlayerOrder(1);" />';
	}
	menu += '</div>';
	
	// build player's container
	var player_container = '<span id="player_' + p.uuid + '"' + ordering + ' draggable="true" class="player"' + coloring + '>'  + menu + flag + '&nbsp;' + p.name + '</span>';
	
	$('#players').append(player_container);
	players[p.uuid] = p;
}

function hidePlayer(uuid) {
	if (uuid in players) {
		$('#player_' + uuid).remove();
		delete players[uuid];
	}
}

// --- dice rolls implementation --------------------------------------

var roll_timeout = 10000.0; // ms until roll will START to disappear

function addRoll(sides, result, name, color, recent) {
	// special case: d2
	var result_label = result
	if (sides == 2) {
		if (result == 2) {
			result_label = '<img style="width: 30px;" src="/static/d2_hit.png" />'
		} else {
			result_label = '<img style="width: 30px;" src="/static/d2_miss.png" />'
		}
	}
	
	// create dice result
	var container = $('#d' + sides + 'rolls');
	css = 'filter: drop-shadow(1px 1px 5px ' + color + ') drop-shadow(-1px -1px 0 ' + color + ');';
	var his_span = '<span style="' + css + '">' + result_label + '</span>';
	css += ' display: none;';
	var box_span = '<span style="' + css + '">' + result_label + '</span>';
	
	if (recent) { 
		container.prepend(box_span);
		
		// prepare automatic cleanup
		var dom_span = container.children(':first-child');
		if (result == 1 || result == sides || sides == 2) {
			dom_span.addClass('natroll');
		}
		dom_span.delay(dice_shake).fadeIn(100, function() {
			dom_span.delay(roll_timeout).fadeOut(2 * roll_timeout, function() { this.remove(); });
		});
	}
	
	// also add to dice history
	var label = '<div style="display: none"><span style="color: ' + color + '">' + name + '</span> d' + sides + ' &rArr; ';
	if (result == 1 || result == sides) {
		label += '<span class="natroll">' + result + '</span>';
	} else {
		label += result;
	}
	label += '</div>';
	$('#historydrop').prepend(label);
	var other_dom_span = $('#historydrop').children(':first-child');
	other_dom_span.delay(dice_shake).fadeIn(1000, function() {});
	
	// and show history
	$('#historydrop').show();
}

// --- ui event handles -----------------------------------------------

function onDrag(event) {
	event.preventDefault();
	pickCanvasPos(event);
	
	if (primary_id != 0) {
		if (drag_action == 'resize') {
			onResize();
		} else if (drag_action == 'rotate') {
			onRotate();
		}
	}
	
	updateTokenbar();
}

function onResize() {
	var first_token = tokens[primary_id] 
	
	// calculate distance between mouse and token   
	var dx = first_token.posx - mouse_x;
	var dy = first_token.posy - mouse_y;
	var scale = Math.sqrt(dx*dx + dy*dy);
	var radius = first_token.size * 0.8;
	
	// normalize distance using distance mouse/icon
	ratio = scale / radius;
	
	// resize all selected tokens
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		if (token.locked) {
			return;
		}
		var size = Math.round(token.size * ratio * 2);
		size = Math.max(min_token_size, Math.min(max_token_size, size));
		// save size
		// @NOTE: resizing is updated after completion, meanwhile
		// clide-side prediction kicks in
		token.size = size;
	});
}

function onRotate(event) { 
	var first_token = tokens[primary_id] 
	
	// calculate vectors between origin/icon and origni/mouse
	// note: assuming the rotation icon is at top
	var icon_box = $('#tokenRotate')[0].getBoundingClientRect();
	var canvas_box = $('#battlemap')[0].getBoundingClientRect();
	icon_dx  = 0
	icon_dy  = -first_token.size * 0.8;
	mouse_dx = mouse_x - first_token.posx;
	mouse_dy = mouse_y - first_token.posy;
	
	// calculate rotation angle
	dotp       = icon_dx * mouse_dx + icon_dy * mouse_dy;
	norm_icon  = first_token.size * 0.8;
	norm_mouse = Math.sqrt(mouse_dx * mouse_dx + mouse_dy * mouse_dy);
	radians    = Math.acos(dotp / (norm_icon * norm_mouse));
	angle      = radians * 180 / 3.14;
	
	if (mouse_dx < 0) {
		angle *= -1;
	}
	
	// rotate all selected tokens
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		if (token.locked) {
			return;
		}
		// save rotation
		// @NOTE: rotation is updated after completion, meanwhile
		// clide-side prediction kicks in
		token.rotate = angle;
	});
}

function onDrop(event) {
	event.preventDefault();
	pickCanvasPos(event);
	
	var queue = $('#uploadqueue')[0];
	queue.files = event.dataTransfer.files;
	
	var f = new FormData($('#uploadform')[0]);
	
	$.ajax({
		url: '/' + gm_name + '/' + game_url + '/upload/' + mouse_x + '/' + mouse_y + '/' + default_token_size,
		type: 'POST',
		data: f,
		contentType: false,
		cache: false,
		processData: false,
		success: function(response) {
			// reset uploadqueue
			$('#uploadqueue').val("");
		}, error: function(response, msg) {
			handleError(response);
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
		var size = token.size * viewport.zoom;
		if (size == -1) {
			size = canvas[0].height;
		} else if (size < 50) {
			size = 50;
		}
		
		// position tokenbar centered to token
		var box = canvas[0].getBoundingClientRect();
		
		$('#tokenbar').css('left', box.left + 'px');
		$('#tokenbar').css('top',  box.top  + 'px');
		$('#tokenbar').css('visibility', '');
		
		$.each(token_icons, function(index, name) { 
			// consider canvas scale (by windows size)  
			var x = token.posx * canvas_scale;
			var y = token.posy * canvas_scale;
			
			// consider viewport position
			x -= viewport.x;
			y -= viewport.y;
			
			// consider viewport zooming (centered)
			x -= canvas[0].width  / 2;
			y -= canvas[0].height / 2;
			x *= viewport.zoom;
			y *= viewport.zoom;    
			x += canvas[0].width  / 2;
			y += canvas[0].height / 2;
			
			// calculate position based on angle
			var degree = 360.0 / token_icons.length;
			var s = Math.sin((-90.0 + index * degree) * 3.14 / 180);
			var c = Math.cos((-90.0 + index * degree) * 3.14 / 180);
			
			x += size * c * 0.8;
			y += size * s * 0.8;
			
			// force position to be on the screen
			x = Math.max(0, Math.min(canvas.width(), x));
			y = Math.max(0, Math.min(canvas.height(), y));
			
			// place icon
			$('#token' + name).css('left', x - 12 + 'px');
			$('#token' + name).css('top',  y - 12 + 'px');
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
	
	// make pos relative to canvas
	var canvas = $('#battlemap')[0];
	var box = canvas.getBoundingClientRect();
	mouse_x = mouse_x - box.left;
	mouse_y = mouse_y - box.top;
	     
	// consider viewport zooming (centered)
	mouse_x -= canvas.width  / 2;
	mouse_y -= canvas.height / 2;
	mouse_x /= viewport.zoom;
	mouse_y /= viewport.zoom;    
	mouse_x += canvas.width  / 2;
	mouse_y += canvas.height / 2;
	
	// consider viewport position
	mouse_x += viewport.x;
	mouse_y += viewport.y;
	
	// consider canvas scale (by windows size)   
	mouse_x /= canvas_scale;
	mouse_y /= canvas_scale;
	
	mouse_x = parseInt(mouse_x);
	mouse_y = parseInt(mouse_y);
}

/// Event handle for start grabbing a token
function onGrab(event) {
	closeGmDropdown();
	
	pickCanvasPos(event);
	
	if (event.buttons == 1) {
		// Left Click: select token
		var token = selectToken(mouse_x, mouse_y);
		
		if (primary_id > 0 && event.shiftKey) {
			// trigger range query from primary token to mouse pos or next token
			var pt = tokens[primary_id];
			var x1 = pt.posx;
			var y1 = pt.posy;
			
			var x2 = mouse_x;
			var y2 = mouse_x;
			
			if (token != null) {
				x2 = token.posx;
				y2 = token.posy;
			}
			
			var adding = false; // default: not adding to the selection
			if (event.ctrlKey) {
				adding = true;
			}
			
			writeSocket({
				'OPID'   : 'RANGE',
				'adding' : adding,
				'left'   : Math.min(x1, x2),
				'top'    : Math.min(y1, y2),
				'width'  : Math.abs(x1 - x2),
				'height' : Math.abs(y1 - y2)
			});
			
		} else if (token != null) {
			var before = select_ids;
			
			if (event.ctrlKey) {
				// toggle token in/out selection group
				var index = select_ids.indexOf(token.id);
				if (index != -1) {
					// remove from selection
					select_ids.splice(index, 1);
				} else {
					// add to selection
					select_ids.push(token.id);
				}
				
			} else {
				// reselect only if token wasn't selected before
				if (!select_ids.includes(token.id)) {
					select_ids = [token.id];
					primary_id = token.id;
					
				} else {
					primary_id = token.id;
				}
				grabbed = true;
			}
			
			if (before != select_ids) {
				// notify server about selection
				writeSocket({
					'OPID'     : 'SELECT',
					'selected' : select_ids
				});
			}
			
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
		var changes = [];
		$.each(select_ids, function(index, id) {
			var token = tokens[id];
			
			if (token.locked) {
				// ignore if locked
				return;
			}
			
			token.rotate = 0;
			token.size   = default_token_size;
			
			changes.push({
				'id'     : id,
				'size'   : token.size,
				'rotate' : token.rotate
			});
		});
		
		writeSocket({
			'OPID'    : 'UPDATE',
			'changes' : changes
		});
	}
}

/// Event handle for releasing a grabbed token
function onRelease() {
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
		
		primary_id = 0;
		
		var adding = false; // default: not adding to the selection
		if (event.ctrlKey) {
			adding = true;
		}
		
		writeSocket({
			'OPID'   : 'RANGE',
			'adding' : adding,
			'left'   : select_from_x,
			'top'    : select_from_y,
			'width'  : select_width,
			'height' : select_height
		});
	}
	
	select_from_x = null;
	select_from_y = null;
	
	updateTokenbar();
}

/// Limit viewport's position
function limitViewportPosition() {
	var dom_canvas = $('#battlemap')[0];
	var width  = dom_canvas.width;
	var height = dom_canvas.height;
	var view_w = width;
	var view_h = height;
	
	var min_x = -view_w / 2;
	var max_x =  view_w / 2;
	
	var min_y = -view_h / 2;
	var max_y =  view_h / 2;
	
	viewport.x = Math.max(min_x, Math.min(max_x, viewport.x));
	viewport.y  = Math.max(min_y, Math.min(max_y, viewport.y));
}

/// Event handle for moving a grabbed token (if not locked)
function onMove(event) {
	pickCanvasPos(event);
	
	if (event.buttons == 1) {
		// left button clicked
		
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
				
				var changes = []
				$.each(select_ids, function(index, id) {
					var t = tokens[id];
					if (!t.locked) {
						// get position relative to primary token
						var dx = t.posx - prev_posx;
						var dy = t.posy - prev_posy;
						// move relative to primary token
						var tx = mouse_x + dx;
						var ty = mouse_y + dy;
						
						changes.push({
							'id'   : id,
							'posx' : tx,
							'posy' : ty
						});
					}
				});
				
				writeSocket({
					'OPID'    : 'UPDATE',
					'changes' : changes
				})
			}
		}
		
	} else if (event.buttons == 4 && zooming) {
		// wheel clicked
		$('#battlemap').css('cursor', 'grab');
		
		dx = event.movementX;
		dy = event.movementY;
		
		// NOTE: some browsers go crazy
		if (dx > 100) { dx /= 100; }
		if (dy > 100) { dy /= 100; }
		
		// move viewport
		viewport.x -= dx / viewport.zoom;
		viewport.y -= dy / viewport.zoom;
		
		limitViewportPosition();
		
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

/// Event handle mouse wheel scrolling
function onWheel(event) {
	if (zooming) {
		// modify zoom
		if (event.deltaY > 0) {
			// zoom out
			viewport.zoom /= 1.05;
			if (viewport.zoom < 0.5) {
				viewport.zoom = 0.5;
			}
		} else if (event.deltaY < 0) {
			// zoom in
			viewport.zoom *= 1.05;
		}
	}
	
	updateTokenbar();
}

/// Event handle to click a dice
function rollDice(sides) {
	$('#d' + sides).addClass('shake');
	
	writeSocket({
		'OPID'  : 'ROLL',
		'sides' : sides
	});
	
	setTimeout(function() {	$('#d' + sides).removeClass('shake'); }, dice_shake);
}

/// Event handle to select all tokens
function selectAllTokens() {
	event.preventDefault();
	
	select_ids = [];
	$.each(tokens, function(index, token) {
		if (token != null && token.size != -1) {
			select_ids.push(token.id);
		}
	});
}

/// Event handle to copy selected tokens
function copySelectedTokens() { 
	event.preventDefault();
	
	copy_tokens = select_ids;
}

/// Event handle to paste copied tokens
function pasteCopiedTokens() {
	event.preventDefault();
	
	if (copy_tokens.length > 0) {
		writeSocket({
			'OPID' : 'CLONE',
			'ids'  : copy_tokens,
			'posx' : mouse_x,
			'posy' : mouse_y
		});
	}
}

/// Event handle to delete selected tokens
function deleteSelectedTokens() { 
	event.preventDefault();
	
	if (select_ids.length > 0) {
		writeSocket({
			'OPID'   : 'DELETE',
			'tokens' : select_ids
		});
	}
}

/// Event handle shortcuts on (first) selected token
function onShortcut(event) {
	if (event.ctrlKey) {
		if (event.keyCode == 65) { // CTRL+A
			selectAllTokens();
			
		} else if (event.keyCode == 67) { // CTRL+C
			copySelectedTokens();
			
		} else if (event.keyCode == 86) { // CTRL+V
			pasteCopiedTokens();
		}
	} else {
		if (event.keyCode == 46) { // DEL
			deleteSelectedTokens();
		}
	}
}

/// Event handle for fliping a token x-wise
function onFlipX() {
	var changes = [];
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		
		if (token.locked) {
			// ignore if locked
			return; 
		}
		token.flipx = !token.flipx;
		
		changes.push({
			'id'    : id,
			'flipx' : token.flipx
		});
	});
	
	writeSocket({
		'OPID'    : 'UPDATE',
		'changes' : changes
	});
}

/// Event handle for (un)locking a token
function onLock() {
	// determine primary lock state
	var primary_lock = false;
	if (primary_id > 0) {
		primary_lock = tokens[primary_id].locked
	}
	
	var changes = [];
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		token.locked = !primary_lock;
		
		changes.push({
			'id'     : id,
			'locked' : token.locked
		});
	});
	
	writeSocket({
		'OPID'    : 'UPDATE',
		'changes' : changes
	});
}

/// Event handle for resize a token
function onStartResize() {
	drag_action = 'resize';
}

/// Event handle for rotating a token
function onStartRotate() {
	drag_action = 'rotate'; 
}

/// Event handle for ending token resize
function onQuitResize() {
	var changes = [];
	$.each(select_ids, function(index, id) {
		changes.push({
			'id'   : id,
			'size' : tokens[id].size
		});
	});
	
	writeSocket({
		'OPID'    : 'UPDATE',
		'changes' : changes
	});
}

/// Event handle for ending token rotate
function onQuitRotate() {
	var changes = [];
	$.each(select_ids, function(index, id) {
		changes.push({
			'id'     : id,
			'rotate' : tokens[id].rotate
		});
	});
	
	writeSocket({
		'OPID'    : 'UPDATE',
		'changes' : changes
	});
}

/// Event handle for quitting rotation/resize dragging
function onQuitAction() {
	if (drag_action == 'rotate') {
		onQuitRotate();
	} else if (drag_action == 'resize') {
		onQuitResize();
	}
	
	drag_action = '';    
}

/// Event handle for moving token to lowest z-order
function onBottom() {
	var changes = [];
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		
		if (token.locked) {
			// ignore if locked
			return;
		}
		// move beneath lowest known z-order
		if (token.locked) {
			token.zorder = 1;
		} else {
			token.zorder = min_z - 1;
			--min_z;
		}
		
		changes.push({
			'id'     : id,
			'zorder' : token.zorder
		});
	});
	
	writeSocket({
		'OPID'    : 'UPDATE',
		'changes' : changes
	});
}

/// Event handle for moving token to hightest z-order
function onTop() { 
	var changes = [];
	$.each(select_ids, function(index, id) {
		var token = tokens[id];
		
		if (token.locked) {
			// ignore if locked
			return;
		}
		// move above highest known z-order
		if (token.locked) {
			token.zorder = -1;
		} else {
			token.zorder = max_z - 1;
			++max_z;
		}
		
		changes.push({
			'id'     : id,
			'zorder' : token.zorder
		});
	});
	
	writeSocket({
		'OPID'    : 'UPDATE',
		'changes' : changes
	});
}

/// Event handle for start dragging a single dice container
function onStartDragDice(sides) {
	drag_player = false;
	if (event.buttons == 1) {
		// select for dragging
		drag_dice = sides;
		
	} else if (event.buttons == 2) {
		// reset dice position
		resetDicePos(sides);
	}
}

/// Event handle for start dragging a players container
function onStartDragPlayers() {
	drag_dice   = null;
	drag_player = true;
}

/// Limit position and align to screen using the container's size
function limitPosition(container, x, y) {
	var w = container.width();
	var h = container.height();
	var x = Math.max(0, Math.min(window.innerWidth - w,  x - w / 2));
	var y = Math.max(0, Math.min(window.innerHeight - h, y - h / 2));
	return [x, y];
}

/// Snaps dice container to the closest edge (from x, y)
function snapDice(x, y, container, default_snap) {
	console.log('snap:', window.innerWidth, window.innerHeight);
	
	var w = container.width();
	var h = container.height();
	
	var min_x = w / 4;
	var min_y = h / 4;
	var max_x = window.innerWidth  - w - w / 4;
	var max_y = window.innerHeight - h - h / 4;
	
	// limit pos to screen
	x = Math.max(min_x, Math.min(x, max_x));
	y = Math.max(min_y, Math.min(y, max_y));
	console.log(min_x, x, max_x, "\t", min_y, y, max_y);
	
	var dx = window.innerWidth  - x; // distance to right
	var dy = window.innerHeight - y; // distance to bottom
	
	if (default_snap == 'left' || x < Math.min(y, dx, dy)) {
		// snap to left
		return [min_x, y, 'left'];
	} else if (default_snap == 'top' || y < Math.min(x, dx, dy)) {
		// snap to top                 
		return [x, min_y, 'top'];   
	} else if (default_snap == 'right' || dx < Math.min(x, y, dy)) {
		// snap to right          
		return [max_x, y, 'right'];
	} else {
		// snap to bottom           
		return[x, max_y, 'bottom'];
	}
}

/// Resets dice container to default position
function resetDicePos(sides) {
	// reset position
	var target = $('#d' + sides + 'box');
	target.css('left', default_dice_pos[sides][0]);
	target.css('top',  default_dice_pos[sides][1]);
	
	// reset cookie
	setCookie('d' + sides, '');
}

/// Drag dice container to position specified by the event
function onDragDice(event) {
	// drag dice box
	var target = $('#d' + drag_dice + 'box');
	 
	// limit position to the screen
	var pos = limitPosition(target, event.clientX, event.clientY)
	
	if (dice_snap) {
		data = snapDice(pos[0], pos[1], target, '');
	}
	
	target.css('left', data[0]);
	target.css('top',  data[1]);
	
	saveDicePos(drag_dice, data);
}

/// Drag players container to position specified by the event
function onDragPlayers(event) {
	var target = $('#players');
	
	// limit position to the screen
	var pos = limitPosition(target, event.clientX, event.clientY)
	
	target.css('left', pos[0]);
	target.css('top',  pos[1]);
	target.css('bottom', '0');
}

/// Event handle for dragging a single dice container
function onDragStuff(event) {
	if (event.buttons == 1) {
		if (drag_dice != null) { 
			onDragDice(event);
		}
		if (drag_player) {
			onDragPlayers(event);
		}
	}
}

/// Event handle for entering a player container with the mouse
function onMouseOverPlayer(uuid) {
	over_player = uuid;
	
	// show player menu
	var menu = $('#playermenu_' + uuid).fadeIn(1500, 0);
}

/// Event handle for leaving a player container with the mouse
function onMouseLeavePlayer(uuid) {
	over_player = null;
	
	// hide player menu
	var menu = $('#playermenu_' + uuid).fadeOut(250, 0);
}

/// Event handle for using the mouse wheel over a player container
function onWheelPlayers() {
	var direction = - Math.sign(event.deltaY);
	
	if (direction != 0) {
		writeSocket({
			'OPID'      : 'ORDER',
			'name'      : players[over_player].name,
			'direction' : direction
		});
	}
}

/// Event handle for moving a player
function onPlayerOrder(direction) {
	if (over_player != null) {
		writeSocket({
			'OPID'      : 'ORDER',
			'name'      : players[over_player].name,
			'direction' : direction
		});
	}
}

/// Event handle for window resize
function onResize(event) {
	// refresh default dice positions
	var total_dice_height = 50 * 7; // 7 dice
	var starty = window.innerHeight / 2 - total_dice_height / 2;
	default_dice_pos[20] = [15, starty    , 'left'];
	default_dice_pos[12] = [15, starty+ 50, 'left'];
	default_dice_pos[10] = [15, starty+100, 'left'];
	default_dice_pos[ 8] = [15, starty+150, 'left'];
	default_dice_pos[ 6] = [15, starty+200, 'left'];
	default_dice_pos[ 4] = [15, starty+250, 'left'];
	default_dice_pos[ 2] = [15, starty+300, 'left'];
	
	console.log('resize', window.innerWidth, window.innerHeight);
	
	// apply dice positions
	$.each(default_dice_pos, function(sides, data) {
		var target = $('#d' + sides + 'box');  
		var data = loadDicePos(sides);
		console.log('d' + sides + ': ', data);
		target.css('left', data[0]);
		target.css('top',  data[1]);
	});
}

/// Load dice position from cookie, returns absolute position
function loadDicePos(sides) { 
	var raw = getCookie('d' + sides)
	if (raw == '') {
		// use default position
		return default_dice_pos[sides];
	}
	var data = JSON.parse(raw);
	
	// calculate absolute position from precentage
	data[0] *= window.innerWidth;
	data[1] *= window.innerHeight;
	
	// handle snap
	if (dice_snap) {
		data = snapDice(data[0], data[1], $('#d' + sides + 'box'), data[2]);
	}
	
	return data;
}

/// Save dice position to cookie using percentage values
function saveDicePos(sides, data) {
	data[0] /= window.innerWidth;
	data[1] /= window.innerHeight;
	setCookie('d' + sides, JSON.stringify(data));
}
