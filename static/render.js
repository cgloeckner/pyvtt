/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/

var target_fps = 90;

var viewport = null;

function resetViewport() {
    viewport = {
        'x'    : MAX_SCENE_WIDTH / 2, // left in [0, 1000]
        'y'    : MAX_SCENE_WIDTH * canvas_ratio / 2,
        'zoom' : 1.0,
        'newx' : null,
        'newy' : null
    };
    
    displayZoom();
};

var allow_auto_movement = true;

function updateViewport() {
    if (!allow_auto_movement) {
        viewport.newx = null;
        viewport.newy = null;
    }
    
    if ((viewport.newx == null || viewport.newy == null)) {
        return;
    }

    var speed = parseInt(interpolation_speed * 1.5);
    // move viewport towards desired position
    if (speed > 0) {
        // interpolate viewport position if necessary
        var dx = viewport.newx - viewport.x;
        var dy = viewport.newy - viewport.y;
        if (Math.abs(dx) > 20 || Math.abs(dy) > 20) {
            // get normalized direction vector
            var d = Math.sqrt(dx * dx + dy * dy);
            // scale vector
            dx = dx * interpolation_speed / d;
            dy = dy * interpolation_speed / d;
            // update position
            viewport.x = parseInt(viewport.x + dx);
            viewport.y = parseInt(viewport.y + dy);    
            
            interpolated = true;
        } else {
            // finish movement
            viewport.x = parseInt(viewport.newx);
            viewport.y = parseInt(viewport.newy);
            viewport.newx = null;
            viewport.newy = null;
        }
    } else {
        // do not interpolate 
        viewport.x = parseInt(viewport.newx);
        viewport.y = parseInt(viewport.newy);
    }

    limitViewportPosition();
}

var ZOOM_MOVE_SPEED   = 20.0;
var ZOOM_FACTOR_SPEED = 1.05;

function displayZoom() {
    if (viewport.zoom > 1.0) {
        $('#zoom').show();
        $('#zoomLevel')[0].innerHTML = 'Zoom: ' + parseInt(viewport.zoom*100) + '%';
    } else {
        $('#zoom').hide();
    }
}

var interpolation_speed = 25; // speed for interpolating between two positions

var canvas_ratio = null;  // aspect ratio

// --- image handling implementation ----------------------------------

var images = [];
var canvas_scale = 1.0; // saved scaling

function resizeCanvas() {
    if (canvas_ratio == null) {
        canvas_ratio = MAX_SCENE_HEIGHT / MAX_SCENE_WIDTH;
    }
    
    var canvas = $('#battlemap');
    
    // avoid breaking aspect ratio
    // note: avoids tokens to be out of view for some players
    var w = window.innerWidth - 10;
    var h = w * canvas_ratio;
    
    // handle too large height
    if (h > window.innerHeight - 45) {
        h = window.innerHeight - 45;
        w = h / canvas_ratio;
    }
    
    // apply size
    canvas[0].width  = w;
    canvas[0].height = h;
    mem_canvas.width  = w;
    mem_canvas.height = h;
    
    // calculate scaling
    canvas_scale = w / MAX_SCENE_WIDTH;

    // force all token labels to be redrawn
    $.each(tokens, function(index, token) {
        if (token != null) {
            token.label_canvas = null;
        }
    });
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


// --- beacon implementation ------------------------------------------

var beacons = {}; // contains beacons keyed by players' uuid

/// Beacon constructor
function Beacon(color) {
    this.cycles = 0;
    this.color  = color;
    this.master = true;
}

/// Add beacon
function addBeacon(color, uuid) {
    beacons[uuid] = new Beacon(color);
}

function startBeacon(beacon, x, y) {
    beacon.x = x;
    beacon.y = y;
                       
    beacon.alpha  = 1.0
    beacon.width  = 5.0;
    beacon.radius = 0;
    beacon.alpha  = 1.0;
    beacon.cycles = 2; 
    beacon.offset = null;
}

function animateBeacon(beacon) {
    if (beacon.cycles > 0) {
        beacon.radius += 1.25;
        if (beacon.radius > 55.0) {
            beacon.radius = 1.5;
            beacon.cycles -= 1;
        }
        beacon.alpha = 1.0 - beacon.radius / 55.0;
    }
    
    // create 2nd beacon (offset)
    if (beacon.master && beacon.offset == null && beacon.alpha < 0.5) {
        beacon.offset = new Beacon(beacon.color);
        startBeacon(beacon.offset, beacon.x, beacon.y);
        // mark as slave (prevent continued recursion)
        beacon.offset.master = false;
    }
}

function drawBeacon(beacon) { 
    animateBeacon(beacon);
                         
    var canvas = $('#battlemap');
    var context = canvas[0].getContext("2d");
    if (beacon.master) { 
    }

    if (beacon.cycles > 0) { 
        context.save();
        
        // handle token position and canvas scale 
        context.translate(beacon.x * canvas_scale, beacon.y * canvas_scale);

        context.beginPath()
        context.globalAlpha = beacon.alpha;
        context.arc(0, 0, beacon.radius / viewport.zoom, 0, 2 * Math.PI, false);
        context.lineWidth = beacon.width / viewport.zoom;
        context.strokeStyle = beacon.color;
        context.stroke();
        context.closePath();
        
        context.restore();
    }
     
    if (beacon.offset != null) {
        drawBeacon(beacon.offset);
    }

    if (beacon.master) {
    }
}

// --- token implementation -------------------------------------------

var tokens         = []; // holds all tokens, updated by the server
var tokens_added   = []; // holds token id => opacity when recently added
var tokens_removed = []; // holds token id => (token, opacity) when recently removed

var player_selections = {}; // buffer that contains selected tokens and corresponding player colors

var culling = []; // holds tokens for culling
var min_z = -1; // lowest known z-order
var max_z =  1; // highest known z-order
var default_token_size = 60;

var background_set = false;

/// Token constructor
function Token(id, url) {
    this.id = id;
    this.posx = 0;
    this.posy = 0;
    this.newx = 0;
    this.newy = 0;
    this.zorder = 0;
    this.size = default_token_size;
    this.url = url;
    this.rotate = 0.0;
    this.flipx = false;
    this.locked = false;
    this.text = null;
    this.color = null;
    this.label_canvas = null;
    this.hue_canvas = null;
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
        if (ratio > canvas_ratio) {
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
function updateToken(data, force=false) {
    // create token if necessary
    if (tokens[data.id] == null) {
        addToken(data.id, data.url);
    }
    
    // ignore position if this client moved it
    var ignore = data.uuid == my_uuid;
    // drop ignore if no client side prediction is enabled
    if (ignore && !client_side_prediction) {
        ignore = false;
    }
    
    // forced updates are ALWAYS applied
    if (force || !ignore) {
        if (!force && grabbed && select_ids.includes(data.id)) {
            // ignore position
        } else {
            // update token data
            if (force) {
                // forced movement: place directly there
                tokens[data.id].posx = data.posx;
                tokens[data.id].posy = data.posy;
            }
            // use given position as target position
            tokens[data.id].newx     = data.posx;
            tokens[data.id].newy     = data.posy;
        }
    }
    
    tokens[data.id].zorder   = data.zorder;
    if (tokens[data.id].size != data.size) {
        // reset canvas for pre-drawn text
        tokens[data.id].label_canvas = null;
        // reset canvas for pre-drawn token hue
        tokens[data.id].hue_canvas   = null;
    }
    tokens[data.id].size     = data.size;
    tokens[data.id].rotate   = data.rotate;
    tokens[data.id].flipx    = data.flipx;
    tokens[data.id].locked   = data.locked;
    if (tokens[data.id].text != data.text || tokens[data.id].color != data.color) {
        // reset canvas for pre-drawn text
        tokens[data.id].label_canvas = null;
        // reset canvas for pre-drawn token hue
        tokens[data.id].hue_canvas   = null;
    }
    tokens[data.id].text     = data.text;
    tokens[data.id].color    = data.color;
    
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
        tokens[data.id].newx = tokens[data.id].posx;
        tokens[data.id].newy = tokens[data.id].posy;
        
        background_set = true;
        
        // hide drophint
        $('#draghint').hide();
    }
}

var num_downloading = 0;
var num_uploading   = 0;

/// Handle uploading notifcation
function notifyUploadStart() {
    if (num_uploading == 0) {
        $('#assetsUploading')[0].innerHTML = '<img src="/static/loading.gif" class="icon" /> <img src="/static/top.png" class="icon" />';
    }
    num_uploading += 1;
}

/// Handle upload finish
function notifyUploadFinish() {
    num_uploading -= 1;
    if (num_uploading == 0) {
        $('#assetsUploading')[0].innerHTML = '';
    }
}

/// Handle downloading notifcation
function notifyDownload(url) {
    if (num_downloading == 0) {
        $('#assetsDownloading')[0].innerHTML = '<img src="/static/loading.gif" class="icon" /> <img src="/static/bottom.png" class="icon" >';
    }
    num_downloading += 1;
    images[url].onload = function() {
        num_downloading -= 1;
        if (num_downloading == 0) {
            $('#assetsDownloading')[0].innerHTML = '';
        }
    }
    images[url].onerror = function() {
        num_downloading -= 1;
        if (num_downloading == 0) {
            $('#assetsDownloading')[0].innerHTML = '';
        }
        console.error('Unable to load ' + url);
    }
}

/// Start loading image into cache
function loadImage(url) {
    if (images[url] == null) {
        if (!quiet) {
            console.info('Loading image ' + url);
        }
        images[url] = new Image();
        notifyDownload(url);
        images[url].src = url;
    }
}

/// Draws a single token (show_ui will show the selection box around it)
function drawToken(token, color, is_background) {
    var canvas = $('#battlemap');
    var context = canvas[0].getContext("2d");
    
    var interpolated = false;
    
    if (interpolation_speed > 0) {
        if (!(grabbed && select_ids.includes(token.id))) {
            // interpolate token position if necessary
            // @NOTE: this is skipped if a token is moved right now
            var dx = token.newx - token.posx;
            var dy = token.newy - token.posy;
            if (Math.abs(dx) > 20 || Math.abs(dy) > 20) {
                // get normalized direction vector
                var d = Math.sqrt(dx * dx + dy * dy);
                // scale vector
                dx = dx * interpolation_speed / d;
                dy = dy * interpolation_speed / d;
                // update position
                token.posx = parseInt(token.posx + dx);
                token.posy = parseInt(token.posy + dy);    
                
                interpolated = true;
            } else {
                // finish movement
                token.posx = parseInt(token.newx);
                token.posy = parseInt(token.newy);
            }
        }
    } else {
        // do not interpolate 
        token.posx = parseInt(token.newx);
        token.posy = parseInt(token.newy);
    }
    
    // cache image if necessary
    loadImage(token.url);
    if (!images[token.url].complete) {
        // skip if not loaded yet
        return;
    }
    
    var sizes = getActualSize(token, canvas[0].width, canvas[0].height);
    sizes[0] *= canvas_scale;
    sizes[1] *= canvas_scale;
    
    context.save();
    
    // handle token position and canvas scale 
    context.translate(token.posx * canvas_scale, token.posy * canvas_scale);
    
    if (is_background) {
        // draw clipped background image
        context.drawImage(
            images[token.url],                    // url
            -sizes[0] / 2, -sizes[1] / 2,        // position
            sizes[0], sizes[1]                    // size
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

        /* @NOTE: feature currently not used
        // alpha-blend large tokens if zoomed in
        if (viewport.zoom > 1.0) {
            if (token.size * viewport.zoom > MAX_SCENE_WIDTH * canvas_ratio) {
                context.globalAlpha = 1 / viewport.zoom;
            }
        }
        */
        
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
        
        // handle selection
        if (color != null) {
            context.shadowColor = color;
            context.shadowBlur = 25;
        }

        var is_timer = token.text.startsWith('#');

        /*if (token.hue_canvas == null && images[token.url].complete) {
            if (token.text != null && is_timer) {
        */
        if (token.text != null && is_timer && token.hue_canvas == null) {
            // create buffer canvas sized like the token
            token.hue_canvas = document.createElement('canvas');
            token.hue_canvas.width  = sizes[0] * viewport.zoom;
            token.hue_canvas.height = sizes[1] * viewport.zoom;
            
            // rotate token's hue if used as timer-token
            var ctx = token.hue_canvas.getContext('2d');
            var hsl = getHsl(token.color);
            ctx.filter = "hue-rotate(" + hsl[0] + "turn) saturate(" + hsl[1] + ") brightness(" + (2*hsl[2]) + ")";

            // pre-render token hue
            ctx.scale(viewport.zoom, viewport.zoom);
            ctx.drawImage(images[token.url], 0, 0, sizes[0], sizes[1]);
        }
        
        // draw token image 
        context.save();
        try {
            var img = images[token.url];
            if (token.hue_canvas != null) {
                img = token.hue_canvas;
            }

            // handle rotation and x-flipping
            context.rotate(token.rotate * 3.14/180.0);
            if (token.flipx) {
                context.scale(-1, 1);
            }
            
            context.drawImage(
                img,                                  // url
                -sizes[0] / 2, -sizes[1] / 2,         // position
                sizes[0], sizes[1]                    // size
            );
        } catch (err) {
            // required to avoid Chrome choking from missing images
        }
        context.restore();
        
        // draw token label
        if (token.text != null) {
            if (token.label_canvas == null) {
                // determine optional fontsize and width
                var fontsize = 15 * canvas_scale;
                if (is_timer) {
                    fontsize *= 2 * token.size / default_token_size;
                }
                context.font = fontsize + 'px sans';
                var metrics = context.measureText(token.text);
                var padding = 14; // to allow for line width
                var width   = metrics.width + padding;
                var height  = fontsize * 96 / 72 + padding;

                // create buffer context
                token.label_canvas = document.createElement('canvas');
                token.label_canvas.width  = width;
                token.label_canvas.height = height;
                ctx = token.label_canvas.getContext('2d');

                // prepare buffer context
                ctx.textAlign  =  "center";
                ctx.fillStyle  = token.color;
                ctx.font       = context.font;
                ctx.lineWidth  = 6;
                ctx.lineJoin   = "round";
                ctx.miterLimit = 2;
                if (brightnessByColor(token.color) > 60) {
                    ctx.strokeStyle = '#000000';
                } else {
                    ctx.strokeStyle = '#FFFFFF'; 
                    ctx.lineWidth   = 4;
                }
                var text = token.text;
                if (is_timer) {   
                    ctx.lineWidth   = 4; 
                    ctx.lineJoin    = "miter";
                    ctx.fillStyle   = '#FFFFFF';
                    ctx.strokeStyle = '#FFFFFF';
                    text = text.substr(1);
                }

                // render label
                ctx.strokeText(text, width/2, height - padding/2);
                ctx.fillText(text, width/2, height - padding/2);
            }
            
            try {
                var left = -token.label_canvas.width/2;
                var top  = token.size/2 - token.label_canvas.height/2;
                if (is_timer) {
                    // vertical center it
                    top = -token.label_canvas.height * 0.6;
                }
                context.scale(Math.sqrt(1/viewport.zoom), Math.sqrt(1/viewport.zoom));
                context.drawImage(token.label_canvas, left, top);
            } catch (error) {
            }
        }
    }
    
    context.restore();
}

var last_update = 0; // timestamp with integer ms
var num_frames  = 0; // number of frames since `last_update` was reset

var running = false; // main loop running?

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
    
    var canvas = $('#battlemap');
    var context = canvas[0].getContext("2d");
    var sizes = [canvas[0].width, canvas[0].height];
    
    context.save();
    
    // handle viewport (zoom where mouse is)
    var rel_x = 0.5;
    var rel_y = 0.5;
    
    context.translate(sizes[0] * rel_x, sizes[1] * rel_y);
    context.scale(viewport.zoom, viewport.zoom);
    context.translate(
        (MAX_SCENE_WIDTH / 2                - viewport.x) * canvas_scale,
        (MAX_SCENE_WIDTH * canvas_ratio / 2 - viewport.y) * canvas_scale
    );
    context.translate(-sizes[0] * rel_x, -sizes[1] * rel_y);
    
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
            color = my_color;
        }
        drawToken(token, color, false);
    });
    
    // draw recently removed tokens (animated)
    $.each(tokens_removed, function(index, token) {
        if (tokens_removed[index] != null) {
            drawToken(tokens_removed[index][0], null, false);
        }
    });

    // draw beacons
    $.each(beacons, function(index, beacon) {
        drawBeacon(beacon);
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
        // consider position and canvas scale
        context.translate(select_from_x * canvas_scale, select_from_y * canvas_scale);
        
        context.beginPath();
        context.rect(0, 0, select_width * canvas_scale, select_height * canvas_scale);
        context.strokeStyle = "#070707";
        context.lineWidth = 1 / viewport.zoom;
        context.fillStyle = "rgba(255, 255, 255, 0.25)";
        context.fillRect(0, 0, select_width * canvas_scale, select_height * canvas_scale);
        context.stroke();
        
        context.restore();
    }
    
    context.restore();
    
    updatePing();
    updateTokenbar();
    updateViewport();
    
    if (!client_side_prediction) {
        updateTokenbar();
    }
    
    // update fps counter
    num_frames += 1;
    var now = Date.now();
    if (now >= last_update + 1000.0) {
        $('#fps')[0].innerHTML = num_frames + ' FPS';
        num_frames = 0;
        last_update = now;
    }
    
    // schedule next drawing
    if (running) {
        setTimeout("drawScene()", 1000.0 / target_fps);
    }
}


 
