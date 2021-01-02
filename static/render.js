/** Powered by PyVTT. Further information: https://github.com/cgloeckner/pyvtt **/

var fps = 60;

var viewport = {
	'left' : 0,
	'top'  : 0,
	'zoom' : 1.0
};

// --- image handling implementation ----------------------------------

var images = [];
var canvas_scale = 1.0; // saved scaling

function resizeCanvas() {
	var canvas = $('#battlemap');
	
	// avoid breaking aspect ratio
	// note: avoids tokens to be out of view for some players
	var w = window.innerWidth - 10;
	var h = w * 0.56;
	
	// handle too large height
	if (h > window.innerHeight - 45) {
		h = window.innerHeight - 45;
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


// --- token implementation -------------------------------------------

var tokens         = []; // holds all tokens, updated by the server
var tokens_added   = []; // holds token id => opacity when recently added
var tokens_removed = []; // holds token id => (token, opacity) when recently removed

var player_selections = {}; // buffer that contains selected tokens and corresponding player colors

var culling = []; // holds tokens for culling
var min_z = -1; // lowest known z-order
var max_z =  1; // highest known z-order
var min_token_size = 50;

var background_set = false;

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
		
		background_set = true;
	}
}

/// Draws a single token (show_ui will show the selection box around it)
function drawToken(token, color, is_background) {
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
	
	context.save();
	
	// handle viewport
	context.translate(-viewport.left, -viewport.top);
	context.scale(viewport.zoom, viewport.zoom);
	
	// handle token position and canvas scale 
	context.translate(token.posx * canvas_scale, token.posy * canvas_scale);
	
	if (is_background) {
		// draw clipped background image
		context.drawImage(
			images[token.url],					// url
			-sizes[0] / 2, -sizes[1] / 2,		// position
			sizes[0], sizes[1]					// size
		);
	} else {
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
		
		// draw token image
		context.drawImage(
			images[token.url],					// url
			-sizes[0] / 2, -sizes[1] / 2,		// position
			sizes[0], sizes[1]					// size
		);
	}
	
	context.restore();
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
		drawToken(background, null, true);
	}
	$.each(culling, function(index, token) {
		var color = null;
		$.each(player_selections, function(cl, tokens) {
			if (tokens.includes(token.id)) {
				color = cl;
			};
		});
		if (color == null && select_ids.includes(token.id)) {
			color = getCookie('playercolor');
		}
		drawToken(token, color, false);
	});
	
	// draw recently removed tokens (animated)
	$.each(tokens_removed, function(index, token) {
		if (tokens_removed[index] != null) {
			drawToken(tokens_removed[index][0], null, false);
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
		
		context.save();         
		// consider viewport
		context.translate(-viewport.left, -viewport.top);
		context.scale(viewport.zoom, viewport.zoom);
		
		// consider position and canvas scale
		context.translate(select_from_x * canvas_scale, select_from_y * canvas_scale);
		
		context.beginPath();
		context.rect(0, 0, select_width * canvas_scale, select_height * canvas_scale);
		context.strokeStyle = "#070707";
		context.fillStyle = "rgba(255, 255, 255, 0.25)";
		context.fillRect(0, 0, select_width * canvas_scale, select_height * canvas_scale);
		context.stroke();
		
		context.restore();
	}
	
	// schedule next drawing
	setTimeout("drawScene()", 1000.0 / fps);
}


 
