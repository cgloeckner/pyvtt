
// --- image handling implementation ------------------------------------------

var images = [];

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

var tokens = [];

function Token(id, url) {
	this.id = id;
	this.posx = 0;
	this.posy = 0;
	this.size = 250;
	this.url = url;
	this.rotate = 0.0;
	this.locked = false;
}

function addToken(id, url) {
	tokens[id] = new Token(id, url);
}

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

function updateToken(data) {
	// create token if necessary
	if (!tokens.includes(data.id)) {
		addToken(data.id, data.url);
	}
	
	// update token data
	tokens[data.id].posx = data.posx;
	tokens[data.id].posy = data.posy;
	tokens[data.id].size   = data.size;
	tokens[data.id].rotate = data.rotate;
	tokens[data.id].flip_x = data.flip_x;
	tokens[data.id].flip_y = data.flip_y;
	tokens[data.id].locked = data.locked;
}

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

var mouse_x = 0;
var mouse_y = 0;

var select_id = 0;
var dragging = false;
var drag_boardcast_tick = 0;

var timeid = 0;

var pull_tick = 0;
var drag_preview_idle = 0;

function handleSelectedToken(token) {
	if (dragging && !token.locked) {
		if (drag_preview_idle > 4) {
			// client side prediction
			token.posx = mouse_x;
			token.posy = mouse_y;
		} else {
			drag_preview_idle += 1;
		}
	}
	drawToken(token, true);
}

$.ajaxSetup({async: false}); // all syncronous ajax calls

function update() {
	if (pull_tick == 0) {
		// pull updates using timeid (will fetch all data since then)
		url = '/ajax/' + game_title + '/update/' + timeid;
		$.getJSON(url, function(data) {
			// update current timeid
			timeid = data['timeid']
			
			console.log(data['full']);
			
			// clear all tokens if a full update was received
			if (data['full']) {
				tokens = [];
			}
			
			// update tokens
			$.each(data['tokens'], function(index, token) {
				updateToken(token);
			});
			
			// show rolls
			$.each(data['rolls'], function(index, info) {
				$('#rolls')[0].append(info + '\n');
			});
		});

		pull_tick = 10;
	} else {
		pull_tick -= 1;
	}
	
	clearCanvas();
	// draw locked tokens
	$.each(tokens, function(index, item) {
		if (item != null && item.locked) {
			if (item.id == select_id) {
				// draw token with ui
				handleSelectedToken(item);
			} else {
				drawToken(item, false);
			}
		}
	});
	// draw unlocked tokens
	$.each(tokens, function(index, item) {
		if (item != null && !item.locked) {
			if (item.id == select_id) {
				// draw token with ui
				handleSelectedToken(item);
			} else {
				drawToken(item, false);
			}
		}
	});
	
	setTimeout("update()", 15);
}

function start(title) {
	game_title = title;
	
	update();
}

function tokenMove() {
	mouse_x = event.offsetX;
	mouse_y = event.offsetY;
	
	if (select_id != 0) {
		var token = tokens[select_id];
		$('#info')[0].innerHTML = 'Token#' + select_id + ' at (' + token.posx + '|' + token.posy + ')';
		
		// NOTE: disabled to better stability
		/*
		if (dragging) {
			if (drag_boardcast_tick == 0) {
				// update position for other players' client-side prediction
				url = '/ajax/' + game_title + '/move/' + select_id + '/' + mouse_x + '/' + mouse_y;
				$.post(url);
				
				//drag_boardcast_tick = 5;
			} else {
				drag_boardcast_tick -= 1;
			}
		}*/
	}
}

function tokenClick() {
	mouse_x = event.offsetX;
	mouse_y = event.offsetY;
	drag_preview_idle = 0;
	
	prev_id = select_id;
	
	select_id = 0;
	var token = selectToken(mouse_x, mouse_y);
	if (token != null) {
		select_id = token.id;
		dragging = true;
		
		$('#info')[0].innerHTML = 'Token#' + select_id + ' at (' + token.posx + '|' + token.posy + ')';
		$('#locked')[0].checked = token.locked;
	}
}

function tokenRelease() {
	if (select_id != 0) {
		url = '/ajax/' + game_title + '/move/' + select_id + '/' + mouse_x + '/' + mouse_y;
		$.post(url);
		
		dragging = false
	}
}

function tokenWheel(event) {
	if (select_id != 0) {
		var token = tokens[select_id];
		if (token.locked) {
			return;
		}
		
		if (event.shiftKey) {
			token.rotate = token.rotate - 5 * event.deltaY;
			if (token.rotate >= 360.0 || token.rotate <= -360.0) {
				token.rotate = 0.0;
			}
			
			var url = '/ajax/' + game_title + '/rotate/' + select_id + '/' + token.rotate;
			$.post(url);
			
		} else {
			token.size = token.size - 5 * event.deltaY;
			if (token.size > 1440) {
				token.size = 1440;
			}
			if (token.size < 16) {
				token.size = 16;
			}
			
			var url = '/ajax/' + game_title + '/resize/' + select_id + '/' + token.size;
			$.post(url);
		}
	}
}

function tokenLock() {
	if (select_id != 0) {
		var lock_it = $('#locked')[0].checked;
		var url = '/ajax/' + game_title + '/lock/' + select_id + '/';
		if (lock_it) {
			url += '1';
		} else {
			url += '0';
		}
		$.post(url);
		
		tokens[select_id].lock = lock_it;
	}
}

function tokenReset() {
	var url = '/ajax/' + game_title + '/resize/' + select_id + '/64';
	$.post(url);
	var url = '/ajax/' + game_title + '/rotate/' + select_id + '/0';
	$.post(url);
}

function tokenStretch() {
	var url = '/ajax/' + game_title + '/resize/' + select_id + '/1000';
	$.post(url);
}

function tokenClone() {
	var url = '/ajax/' + game_title + '/clone/' + select_id;
	$.post(url);
}

function tokenDelete(event) {
	var url = '/ajax/' + game_title + '/delete/' + select_id;
	$.post(url);
}

function rollDice(sides) {
	var url = '/roll/' + game_title + '/SHITFACE/' + sides
	$.post(url);
}

function clearRolls() {
	var url = '/clear_rolls/' + game_title;
	$.post(url);

	$('#rolls')[0].innerHTML = '';
}

function clearVisible() {
	var url = '/clear_tokens/' + game_title + '/players';
	$.post(url);
}

function clearGmArea() {
	var url = '/clear_tokens/' + game_title + '/gm';
	$.post(url);

}



