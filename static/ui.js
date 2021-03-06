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

var over_player  = null;    // indicates over which player the mouse is located (by name)

var default_dice_pos = {};  // default dice positions

var client_side_prediction = true; // enable/disable client side prediction (atm used for movement only)

var space_bar = false; // whether spacebar is pressed

var token_rotate_lock_threshold = 15; // threshold for lock-in a token rotation
var token_last_angle = null;

var fade_dice = true;

var dice_sides = [2, 4, 6, 8, 10, 12, 20];

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
        menu += '<img src="/static/left.png" draggable="false" class="left" onClick="onPlayerOrder(-1);" />'
    }
    if (is_gm && p.uuid != my_uuid) {
        menu += '<img src="/static/kick.gif" draggable="false" class="center" onClick="kickPlayer(\'' + game_url + '\', \'' + p.uuid + '\');" />';
    }
    if (!p.is_last) {
        menu += '<img src="/static/right.png" draggable="false" class="right" onClick="onPlayerOrder(1);" />';
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
    // handling min-/max-rolls
    var ani_css = '';
    var lbl_css = '';
    if (result == 1) {
        ani_css = 'minani';
        lbl_css = ' minroll';
    } else if (result == sides) {
        ani_css = 'maxani';
        lbl_css = ' maxroll';
    }
    rslt_css = '';
    
    // special case: d2
    var result_label = result
    if (sides == 2) {
        if (result == 2) {
            result_label = '&#x2620;'; // skull
            rslt_css += ' skull' ;
        } else {
            result_label = '&mdash;'; // slash
        }
    } 
    
    if (recent) {
        // create dice result
        var parent_span = '<span style="display: none;">';
        var box_span    = '<span class="roll' + lbl_css + '" style="border: 3px inset ' + color + ';">';
        var result_span = '<span class="result' + rslt_css + '">';
        var player_span = '<span class="player">';
        var dice_result_span =
            parent_span + '\n'
                + '\t' + box_span + '\n'
                    + '\t\t' + result_span + result_label + '</span>\n'
                    + '\t\t' + player_span + name + '</span>\n'
                + '\t</span>\n'
                + '\t<span class="' + ani_css + '"></span>\n'
            + '</span>';
         
        var container = $('#d' + sides + 'rolls');
        container.prepend(dice_result_span);
        
        // prepare automatic cleanup
        var dom_span = container.children(':first-child');
        dom_span.delay(dice_shake).fadeIn(100, function() {
            if (fade_dice) {
                dom_span.delay(roll_timeout).fadeOut(500, function() { this.remove(); });
            }
        });
        
        if (ani_css == 'maxani') {
            // let animation fade out earlier
            var ani = $(dom_span.children()[1]);
            ani.delay(3000).fadeOut(500);
        }
    };
}

// --- ui event handles -----------------------------------------------

var drag_img = new Image(); // Replacement for default drag image
drag_img.src = '/static/transparent.png'


function onDrag(event) {
    var drag_data = localStorage.getItem('drag_data');
    console.log('onDrag = ', drag_data, '!')
    
    event.preventDefault();
    pickCanvasPos(event);
    
    if (drag_data == 'players') {
        onDragPlayers(event);
        
    } else if (primary_id != 0) {        
        if (drag_data == 'resize') {
            onTokenResize();
        } else if (drag_data == 'rotate') {
            onTokenRotate();
        }
    } else { 
        onDragDice(event);
    }
}

function onResizeReset(event) {
    if (event.buttons == 2) {
        var changes = [];
        $.each(select_ids, function(index, id) {
            var token = tokens[id];
            
            if (token.locked) {
                // ignore if locked
                return;
            }
            
            token.size   = default_token_size;
            
            changes.push({
                'id'     : id,
                'size'   : token.size
            });
        });
        
        writeSocket({
            'OPID'    : 'UPDATE',
            'changes' : changes
        });
    }
}

function onRotateReset(event) {
    if (event.buttons == 2) {
        var changes = [];
        $.each(select_ids, function(index, id) {
            var token = tokens[id];
            
            if (token.locked) {
                // ignore if locked
                return;
            }
            
            token.rotate = 0.0;
            
            changes.push({
                'id'     : id,
                'rotate' : token.rotate
            });
        });
        
        writeSocket({
            'OPID'    : 'UPDATE',
            'changes' : changes
        });
    }
}

function onTokenResize() {
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
        size = Math.max(min_token_resize, Math.min(max_token_resize, size));
        // save size
        // @NOTE: resizing is updated after completion, meanwhile
        // clide-side prediction kicks in
        token.size = size;
    });
}

function onTokenRotate(event) { 
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
    
    // try to lock token to multiples of 90 degree
    if (Math.abs(angle) < token_rotate_lock_threshold) {
        angle = 0;
    }
    if (Math.abs(angle-90) < token_rotate_lock_threshold) {
        angle = 90;
    }
    if (Math.abs(angle-180) < token_rotate_lock_threshold) {
        angle = 180;
    }
    if (Math.abs(angle-270) < token_rotate_lock_threshold) {
        angle = 270;
    }
    
    if (mouse_dx < 0) {
        angle *= -1;
    }
    
    // rotate all selected tokens
    $.each(select_ids, function(index, id) {
        var token = tokens[id];
        if (token.locked) {
            return;
        }
        
        // undo last rotation
        if (token_last_angle != null) {
            token.rotate -= token_last_angle;
        }
        
        // apply rotation
        // @NOTE: rotation is updated after completion, meanwhile
        // clide-side prediction kicks in
        token.rotate += angle;
    });
    
    token_last_angle = angle;
}

function onDrop(event) {
    event.preventDefault();
    pickCanvasPos(event);

    if (localStorage.getItem('drag_data') != null) {
        // ignore
        return;
    }
    
    showInfo('LOADING');
    
    // test upload data sizes
    var queue = $('#uploadqueue')[0];
    queue.files = event.dataTransfer.files;
    var sizes_ok = true;
    
    var max_filesize = MAX_TOKEN_FILESIZE;
    var file_type = 'TOKEN';
    $.each(queue.files, function(index, file) {
        max_filesize = MAX_TOKEN_FILESIZE;
        if (index == 0 && !background_set) {
            // no background set, first image is used as background
            max_filesize = MAX_BACKGROUND_FILESIZE;
        }
        if (file.size > max_filesize * 1024 * 1024) {
            if (max_filesize == MAX_BACKGROUND_FILESIZE) {
                file_type = 'BACKGROUND';
            }
            sizes_ok = false;
        }
    });
    if (!sizes_ok) {
        showError('TOO LARGE ' + file_type + ' (MAX ' + max_filesize + ' MiB)');
        return;
    }
    
    // fetch upload data
    var f = new FormData($('#uploadform')[0]);
    
    $.ajax({
        url: '/' + gm_name + '/' + game_url + '/upload',
        type: 'POST',
        data: f,
        contentType: false,
        cache: false,
        processData: false,
        success: function(response) {
            // reset uploadqueue
            $('#uploadqueue').val("");
            
            // load images if necessary
            var urls = JSON.parse(response);
            $.each(urls, function(index, url) {
                loadImage(url);
            });
            
            // trigger token creation via websocket
            writeSocket({
                'OPID' : 'CREATE',
                'posx' : mouse_x,
                'posy' : mouse_y,
                'size' : default_token_size,
                'urls' : urls
            });
            
            $('#popup').hide();
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
        var canvas_pos = canvas.position()
        var x = token.posx;
        var y = token.posy;
          
        // consider viewport position
        x -= viewport.x;
        y -= viewport.y;
        x += MAX_SCENE_WIDTH / 2;
        y += MAX_SCENE_WIDTH * canvas_ratio / 2;
        
        // consider viewport zooming (centered)
        x -= MAX_SCENE_WIDTH / 2;
        y -= MAX_SCENE_WIDTH / 2 * canvas_ratio;
        x *= viewport.zoom;
        y *= viewport.zoom;    
        x += MAX_SCENE_WIDTH / 2;
        y += MAX_SCENE_WIDTH / 2 * canvas_ratio;
        
        // consider canvas scale (by windows size)  
        x *= canvas_scale;
        y *= canvas_scale;
        
        $('#tokenbar').css('left', canvas_pos.left + 'px');
        $('#tokenbar').css('top',  canvas_pos.top  + 'px');
        $('#tokenbar').css('visibility', 'visible');
        
        $.each(token_icons, function(index, name) { 
            // calculate position based on angle
            var degree = 360.0 / token_icons.length;
            var s = Math.sin((-index * degree) * 3.14 / 180);
            var c = Math.cos((-index * degree) * 3.14 / 180);
            
            var radius = size * 0.8 * canvas_scale;
            var icon_x = x - radius * s;
            var icon_y = y - radius * c;
            
            // force position to be on the screen
            icon_x = Math.max(0, Math.min(canvas.width(), icon_x));
            icon_y = Math.max(0, Math.min(canvas.height(), icon_y));
            
            // place icon
            var icon = $('#token' + name);
            var w = icon.width();
            var h = icon.height();
            icon.css('left', icon_x - w / 2 + 'px');
            icon.css('top',  icon_y - h / 2 + 'px');
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
    
    // consider canvas scale (by windows size)   
    mouse_x /= canvas_scale;
    mouse_y /= canvas_scale;
    
    // consider viewport zooming (centered)
    mouse_x -= MAX_SCENE_WIDTH / 2;
    mouse_y -= MAX_SCENE_WIDTH * canvas_ratio / 2;
    mouse_x /= viewport.zoom;
    mouse_y /= viewport.zoom;     
    mouse_x += MAX_SCENE_WIDTH / 2;
    mouse_y += MAX_SCENE_WIDTH * canvas_ratio / 2;
    
    // consider (centered) viewport position
    mouse_x += viewport.x;
    mouse_y += viewport.y;
    mouse_x -= MAX_SCENE_WIDTH / 2;
    mouse_y -= MAX_SCENE_WIDTH * canvas_ratio / 2;
    
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
    var was_grabbed = grabbed;
    if (select_ids.length > 0) {
        grabbed = false;
    }
    
    $('#battlemap').css('cursor', 'default');
    
    if (primary_id != 0 && was_grabbed) {
        var changes = []
        
        $.each(select_ids, function(index, id) {
            var t = tokens[id];
            if (!t.locked) {
                changes.push({
                    'id'   : id,
                    'posx' : parseInt(t.newx),
                    'posy' : parseInt(t.newy)
                });
            }
        });
        
        writeSocket({
            'OPID'    : 'UPDATE',
            'changes' : changes
        });
    }
    
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
}

/// Limit viewport's position
function limitViewportPosition() {
    var canvas = $('#battlemap')[0];
    var width  = MAX_SCENE_WIDTH;
    var height = MAX_SCENE_WIDTH * canvas_ratio;
    
    // calculate visible area
    var visible_w = width  / viewport.zoom;
    var visible_h = height / viewport.zoom;
    
    var min_x = visible_w / 2; 
    var min_y = visible_h / 2;
    var max_x = width  - min_x;
    var max_y = height - min_y;
    
    viewport.x = Math.max(min_x, Math.min(max_x, viewport.x));
    viewport.y = Math.max(min_y, Math.min(max_y, viewport.y));
}

/// Event handle for moving a grabbed token (if not locked)
function onMove(event) {
    pickCanvasPos(event);
    
    var battlemap = $('#battlemap');
    var w = battlemap.width();
    var h = battlemap.height();
    
    if (event.buttons == 1 && !space_bar) {
        // left button clicked
        
        if (primary_id != 0 && grabbed) {
            var token = tokens[primary_id];
             
            // transform cursor
            if (token == null) {
                battlemap.css('cursor', 'default');
            } else if (token.locked) {
                battlemap.css('cursor', 'not-allowed');
            } else {                                         
                battlemap.css('cursor', 'grab');
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
                        
                        // limit pos to screen (half size as padding)
                        // @NOTE: padding isn't enough (see: resize, rotation), maybe it's even desired not do pad it
                        /*var size = getActualSize(token, battlemap.width(), battlemap.height());
                        var padding_x = parseInt(size[0] / 2);
                        var padding_y = parseInt(size[1] / 2);
                        */
                        var padding_x = 0;
                        var padding_y = 0;
                        tx = Math.max(padding_x, Math.min(tx, MAX_SCENE_WIDTH                - padding_x));
                        ty = Math.max(padding_y, Math.min(ty, MAX_SCENE_WIDTH * canvas_ratio - padding_y));
                        
                        if (client_side_prediction) {
                            // client-side predict (immediately place it there)
                            t.posx = tx;
                            t.posy = ty;
                        }
                        t.newx = tx;
                        t.newy = ty;
                        
                        changes.push({
                            'id'   : id,
                            'posx' : parseInt(tx),
                            'posy' : parseInt(ty)
                        });
                    }
                });
                
                // not push every position to go easy on the server
                if (socket_move_timeout <= Date.now()) {
                    writeSocket({
                        'OPID'    : 'UPDATE',
                        'changes' : changes
                    });
                    socket_move_timeout = Date.now() + socket_move_delay;
                }
            }
        }
        
    } else if ((event.buttons == 4 || (event.buttons == 1 && space_bar)) && zooming) {
        // wheel clicked
        battlemap.css('cursor', 'grab');
        
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
            battlemap.css('cursor', 'default');
        } else if (token.locked) {
            battlemap.css('cursor', 'not-allowed');
        } else {                                         
            battlemap.css('cursor', 'grab');
        }
    }
}

/// Event handle mouse wheel scrolling
function onWheel(event) {
    if (zooming) {
        var show = false;
        var canvas = $('#battlemap');
        
        // default: zoom using viewport's center
        var reference_x = viewport.x;
        var reference_y = viewport.y;
        
        // modify zoom
        if (event.deltaY > 0) {
            // zoom out
            viewport.zoom /= ZOOM_FACTOR_SPEED;
            if (viewport.zoom < 1.0) {
                viewport.zoom = 1.0;
            }
            show = true;
        } else if (event.deltaY < 0) {
            // zoom in
            viewport.zoom *= ZOOM_FACTOR_SPEED;
            show = true;
            
            // zoom using mouse position
            reference_x = mouse_x;
            reference_y = mouse_y;
        }
        
        // calculate view's position
        var rel_x = reference_x / MAX_SCENE_WIDTH;
        var rel_y = reference_y / (MAX_SCENE_WIDTH * canvas_ratio);
        var x = MAX_SCENE_WIDTH * rel_x;
        var y = MAX_SCENE_WIDTH * canvas_ratio * rel_y;
        
        // shift viewport position slightly towards desired direction
        if (x > viewport.x) {
            viewport.x += ZOOM_MOVE_SPEED / viewport.zoom;
            if (viewport.x > x) {
                viewport.x = x;
            }
        } else if (x < viewport.x) {
            viewport.x -= ZOOM_MOVE_SPEED / viewport.zoom;
            if (viewport.x < x) {
                viewport.x = x;
            }
        }
        if (y > viewport.y) {
            viewport.y += ZOOM_MOVE_SPEED / viewport.zoom;
            if (viewport.y > y) {
                viewport.y = y;
            }
        } else if (y < viewport.y) {
            viewport.y -= ZOOM_MOVE_SPEED / viewport.zoom;
            if (viewport.y < y) {
                viewport.y = y;
            }
        }
        
        limitViewportPosition();
        
        displayZoom();
    }
}

/// Event handle to click a dice
function rollDice(sides) {
    // trigger dice shaking and poof (by re-applying CSS class)
    var target = $('#d' + sides + 'icon');
    var poofani = $('#d' + sides + 'poofani');      
    // @NOTE: delay required (else nothing will happen) 
    target.removeClass('shake').hide().delay(10).show().addClass('shake');
    poofani.removeClass('dicepoof').hide().delay(10).show().addClass('dicepoof');
    
    writeSocket({
        'OPID'  : 'ROLL',
        'sides' : sides
    }); 
}

function toggleDiceHistory() {
    var history = $('#dicehistory');
    
    if (history.css('display') == 'none') {
        history.fadeIn(500);
    } else {
        history.fadeOut(500);
    }
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
    space_bar = event.keyCode == 32;
    
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

/// Event handle for releasing a key
function onKeyRelease(event) {
    space_bar = false;
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
    event.dataTransfer.setDragImage(drag_img, 0, 0);
    localStorage.setItem('drag_data', 'resize');
}

/// Event handle for rotating a token
function onStartRotate() {            
    event.dataTransfer.setDragImage(drag_img, 0, 0);
    
    localStorage.setItem('drag_data', 'rotate');
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
    
    token_last_angle = null;
}

/// Event handle for quitting rotation/resize dragging
function onQuitAction(event) {           
    var action = localStorage.getItem('drag_data');
    if (action == 'rotate') {
        onQuitRotate();
    } else if (action == 'resize') {
        onQuitResize();
    }

    localStorage.removeItem('drag_data');
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
            token.zorder = max_z + 1;
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
function onStartDragDice(event, sides) {
    event.dataTransfer.setDragImage(drag_img, 0, 0);
    localStorage.setItem('drag_data',  sides);
}

/// Event handle for clicking a single dice container
function onResetDice(event, sides) {
    if (event.buttons == 2) {
        // reset dice position
        resetDicePos(sides);
    }
}
   
/// Event handle for stop dragging a single dice container
function onEndDragDice(event) {
    localStorage.removeItem('drag_data');
}

/// Event handle for start dragging the players container
function onStartDragPlayers(event) {         
    event.dataTransfer.setDragImage(drag_img, 0, 0);
    localStorage.setItem('drag_data', 'players');
}

/// Event handle for clicking the players container
function onResetPlayers(event) {
    if (event.buttons == 2) {
        // reset players position
        var target = $('#players');
        var pos = [window.innerWidth * 0.5, window.innerHeight - target.height()];
        
        // apply position
        movePlayersTo(pos);
        localStorage.removeItem('players');
    }
}
   
/// Event handle for stop dragging the players container
function onEndDragPlayers(event) {
    localStorage.removeItem('drag_data');
}

/// Snaps dice container to the closest edge (from x, y)
function snapDice(x, y, container, default_snap) {
    var w = container.width();
    var h = container.height();
    
    var min_x = w / 4;
    var min_y = h / 4;
    var max_x = window.innerWidth  - w - w / 4;
    var max_y = window.innerHeight - h - h / 4;
    
    // limit pos to screen
    x = Math.max(min_x, Math.min(x, max_x));
    y = Math.max(min_y, Math.min(y, max_y));
    
    var dx = window.innerWidth  - x; // distance to right
    var dy = window.innerHeight - y; // distance to bottom
    
    if (default_snap == 'left' || x <= Math.min(y, dx, dy)) {
        // snap to left
        return [min_x, y, 'left'];
    } else if (default_snap == 'top' || y <= Math.min(x, dx, dy)) {
        // snap to top                 
        return [x, min_y, 'top'];   
    } else if (default_snap == 'right' || dx <= Math.min(x, y, dy)) {
        // snap to right          
        return [max_x, y, 'right'];
    } else {
        // snap to bottom           
        return [x, max_y, 'bottom'];
    }
}

/// Resets dice container to default position
function resetDicePos(sides) { 
    localStorage.removeItem('d' + sides);
    
    // move to default pos
    var data = [default_dice_pos[sides][0], default_dice_pos[sides][1], 'left'];
    moveDiceTo(data, sides);
}

function moveDiceTo(data, sides) {
    var icon  = $('#d' + sides + 'icon');
    var rolls = $('#d' + sides + 'rolls');
    
    // change position
    var icon = $('#d' + sides + 'icon');
    icon.css('left', data[0]);
    icon.css('top',  data[1]);
    
    var w = icon.width();
    var h = icon.height();
    
    // change rollbox (pos + orientation) and history (pos)
    switch (data[2]) {
        case 'left':
            rolls.css('left',   w * 1.5);
            rolls.css('right',  0);
            rolls.css('top',    data[1]);
            rolls.css('bottom', 0);          
            rolls.css('display', 'inline-flex');
            rolls.css('flex-direction', 'row');
            break;
        case 'top': 
            rolls.css('left',   data[0]);
            rolls.css('right',  0);
            rolls.css('top',    h * 1.5 - w/4);
            rolls.css('bottom', 0);
            rolls.css('display', 'flex');
            rolls.css('flex-direction', 'column');
            break;
        case 'right':
            rolls.css('left',   0);
            rolls.css('right',  w * 1.5);
            rolls.css('top',    data[1]);
            rolls.css('bottom', 0);
            rolls.css('display', 'inline-flex');
            rolls.css('flex-direction', 'row-reverse');
            break;
        case 'bottom': 
            rolls.css('left',   data[0]);
            rolls.css('right',  0);
            rolls.css('top',    0);
            rolls.css('bottom', h * 1.5 - w/4);
            rolls.css('display', 'flex');
            rolls.css('flex-direction', 'column-reverse');
            break;
    }
    
    // change dice history position
}

function movePlayersTo(pos) {
    var target = $('#players')
    target.css('left', pos[0]);
    target.css('top',  pos[1]);
}

/// Drag dice container to position specified by the event
function onDragDice(event) {
    var sides = localStorage.getItem('drag_data');
    
    // drag dice box
    var target = $('#d' + sides + 'icon');
     
    // limit position to the screen
    var w = target.width();
    var h = target.height();
    var x = Math.max(0, Math.min(window.innerWidth - w,  event.clientX - w / 2));
    var y = Math.max(0, Math.min(window.innerHeight - h, event.clientY - h / 2));
    var data = [x, y];
    data = snapDice(data[0], data[1], target, '');
    
    // apply position
    moveDiceTo(data, sides);
    saveDicePos(sides, data);
}

/// Drag players container to position specified by the event
function onDragPlayers(event) {
    var target = $('#players');
    
    // limit position to the screen
    var w = target.width();
    var h = target.height();
    var x = Math.max(w / 2, Math.min(window.innerWidth - w/2, event.clientX));
    var y = Math.max(0,     Math.min(window.innerHeight - h,  event.clientY));
    var pos = [x, y];
    
    movePlayersTo(pos);
    savePlayersPos(pos);
}

/*
/// Event handle for dragging a single dice container
function onDragStuff(event) {
}
*/
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
function onWindowResize(event) {
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
    
    // apply dice positions
    $.each(default_dice_pos, function(sides, data) {
        var data = loadDicePos(sides);
        moveDiceTo(data, sides);
    });
    
    // fix players position
    var players_pos = loadPlayersPos();
    movePlayersTo(players_pos);
}

/// Load dice position from local storage, returns absolute position
function loadDicePos(sides) { 
    var raw = localStorage.getItem('d' + sides);
    if (raw == null) {
        // use default position
        return default_dice_pos[sides];
    }
    var data = JSON.parse(raw);
    
    // calculate absolute position from precentage
    data[0] *= window.innerWidth;
    data[1] *= window.innerHeight;
    
    // handle snap
    data = snapDice(data[0], data[1], $('#d' + sides + 'icon'), data[2]);
    
    return data;
}

/// Save dice position to local storage using percentage values
function saveDicePos(sides, data) {
    data[0] /= window.innerWidth;
    data[1] /= window.innerHeight;
    localStorage.setItem('d' + sides, JSON.stringify(data));
}

/// Load players position from local storage, returns absolute position
function loadPlayersPos() {
    var raw = localStorage.getItem('players');
    if (raw == null) {
        // default position: bottom center
        var target = $('#players');
        return [window.innerWidth * 0.5, window.innerHeight - target.height()];
    }
    var data = JSON.parse(raw) 
    // calculate absolute position from precentage
    data[0] *= window.innerWidth;
    data[1] *= window.innerHeight;
    
    return data;
}

/// Save players position to local storage using percentage values
function savePlayersPos(pos) {
    pos[0] /= window.innerWidth;
    pos[1] /= window.innerHeight;
    localStorage.setItem('players', JSON.stringify(pos));
}

function getImageBlob(img) {
    var tmp_canvas = document.createElement("canvas");
    tmp_canvas.width  = img.width;
    tmp_canvas.height = img.height;
    var ctx = tmp_canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);
    url = tmp_canvas.toDataURL("image/png");
    
    var arr  = url.split(',');
    var mime = arr[0].match(/:(.*?);/)[1];
    var bstr = atob(arr[1]);
    var n = bstr.length;
    var u8arr = new Uint8Array(n);
    while (n--) {
         u8arr[n] = bstr.charCodeAt(n);
    }
    return new Blob([u8arr], {type: mime});
}

function ignoreBackground() {
    showInfo('LOADING');

    // load transparent image from URL
    var img = new Image()
    img.src = '/static/transparent.png';
    img.onload = function() {
        var blob = getImageBlob(img);
        var f = new FormData();
        f.append('file[]', blob, 'transparent.png');

        // upload as background (assuming nobody else is faster :D )
        $.ajax({
            url: '/' + gm_name + '/' + game_url + '/upload',
            type: 'POST',
            data: f,
            contentType: false,
            cache: false,
            processData: false,
            success: function(response) {
                // reset uploadqueue
                $('#uploadqueue').val("");
                
                // load images if necessary
                var urls = JSON.parse(response);
                $.each(urls, function(index, url) {
                    loadImage(url);
                });
                
                // trigger token creation via websocket
                writeSocket({
                    'OPID' : 'CREATE',
                    'posx' : 0,
                    'posy' : 0,
                    'size' : -1,
                    'urls' : urls
                });
                
                $('#popup').hide();
            }, error: function(response, msg) {
                handleError(response);
            }
        });
    };
}
