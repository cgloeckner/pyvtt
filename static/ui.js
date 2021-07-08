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

var over_player  = null;    // indicates over which player the mouse is located (by name)

var default_dice_pos = {};  // default dice positions

var client_side_prediction = true; // enable/disable client side prediction (atm used for movement only)

var space_bar = false; // whether spacebar is pressed

var token_rotate_lock_threshold = 15; // threshold for lock-in a token rotation
var token_last_angle = null;

var fade_dice = true;

var SCREEN_BORDER_WIDTH = 0.1; // percentage of screen which is used as border for dragging dice

var dice_sides = [2, 4, 6, 8, 10, 12, 20];

var touch_start = null; // starting point for a touch action
var touch_force = 0.0;
var was_scrolled = false; // indicates whether viewport was dragged/scrolled

// implementation of a double left click
var initial_click = 0;
var double_click_limit = 200;


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
function Player(name, uuid, color, ip, country, flag, index) {
    this.name    = name;
    this.uuid    = uuid;
    this.color   = color;
    this.ip      = ip;
    this.country = country;
    this.flag    = flag;
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

    // create player container (uuid as id, custom colored, optional kick click, draggable)
    var coloring = ' style="filter: drop-shadow(1px 1px 9px ' + p.color + ') drop-shadow(-1px -1px 0 ' + p.color + ');"';
    var ordering = ' onMouseEnter="onMouseOverPlayer(\'' + p.uuid + '\');"';
       ordering += ' onMouseLeave="onMouseLeavePlayer(\'' + p.uuid + '\');"';
    
    // create player menu for this player
    var menu = '<div class="playermenu" id="playermenu_' + p.uuid + '">'
    if (p.index > 0) {
        menu += '<img src="/static/left.png" draggable="false" class="left" title="MOVE TO LEFT" onClick="onPlayerOrder(-1);" />'
    }
    if (is_gm && p.uuid != my_uuid) {
        menu += '<img src="/static/delete.png" draggable="false" class="center" title="KICK PLAYER" onClick="kickPlayer(\'' + game_url + '\', \'' + p.uuid + '\');" />';
    }
    if (!p.is_last) {
        menu += '<img src="/static/right.png" draggable="false" class="right" title="MOVE TO RIGHT" onMouseLeave="hideHint();" onClick="onPlayerOrder(1);" />';
    }
    menu += '</div>';
    
    // build player's container
    var player_container = '<span id="player_' + p.uuid + '"' + ordering + ' draggable="true" class="player"' + coloring + '>'  + menu + p.flag + '&nbsp;' + p.name + '</span>';

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

var roll_history = {}; // save each player's last dice roll per die

function addRoll(sides, result, name, color, recent) {
    roll_history[sides + '_' + name] = result;
    
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

    // special case: d100
    if (sides == 100) {
        // use d10's results box
        sides = 10;
        if (result < 10) {
            result_label = '0' + result;
        } else if (result == 100) {
            result_label = '00';
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
    
    event.preventDefault();
    pickCanvasPos(event);

    if (drag_data == 'players') {
        onDragPlayers(event);

    } else if (drag_data == 'music') {
        onDragMusic(event);
        
    } else if (primary_id != 0) {        
        if (drag_data == 'resize') {
            onTokenResize(event);
        } else if (drag_data == 'rotate') {
            onTokenRotate(event);
        }
    } else {
        onDragDice(event);
    }
}

/// Event handle to perform dice dragging by touch
function onMobileDragDice(event, d) {
    localStorage.setItem('drag_data', d);
    onDragDice(event);
}

function onTokenResize(event) {      
    event.preventDefault();
    
    var first_token = tokens[primary_id];
    
    // calculate distance between mouse and token   
    var dx = first_token.posx - mouse_x;
    var dy = first_token.posy - mouse_y;
    var scale = Math.sqrt(dx*dx + dy*dy);
    var radius = first_token.size * 0.8;

    // normalize distance using distance mouse/icon
    ratio = scale / radius;

    // determine min token size based on current zoom
    tmp_min_token_size = parseInt(default_token_size / (1.44 * viewport.zoom));
    
    // resize all selected tokens
    $.each(select_ids, function(index, id) {
        var token = tokens[id];
        if (token == null || token.locked) {
            return;
        }
        var size = Math.round(token.size * ratio * 2);
        size = Math.max(tmp_min_token_size, Math.min(MAX_TOKEN_SIZE, size));
        // save size
        // @NOTE: resizing is updated after completion, meanwhile
        // clide-side prediction kicks in
        token.size = size;

        // trigger buffer redraw
        token.label_canvas = null;
        token.hue_canvas   = null;
    });
}

function onTokenRotate(event) { 
    event.preventDefault();
    
    var first_token = tokens[primary_id];
    
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
        if (token == null || token.locked) {
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

function isSingleAudio(queue) {
    return queue.files.length == 1 && queue.files[0].type == 'audio/mpeg';
}

function onDrop(event) {
    event.preventDefault();
    pickCanvasPos(event);

    if (localStorage.getItem('drag_data') != null) {
        // ignore
        return;
    }
    
    notifyUploadStart();
    
    // test upload data sizes
    var queue = $('#uploadqueue')[0];
    queue.files = event.dataTransfer.files;

    var error_msg = '';
    $.each(event.dataTransfer.files, function(index, file) {
        if (error_msg != '') {
            notifyUploadFinish();
            return;
        }
        
        content = file.type.split('/')[0];
        
        var max_filesize = 0;
        var file_type    = '';
        // check image filesize
        if (content == 'image') {
            max_filesize = MAX_TOKEN_FILESIZE;
            file_type    = 'TOKEN';
            if (index == 0 && !background_set) {
                // first file is assumed as background image
                max_filesize = MAX_BACKGROUND_FILESIZE
                file_type = 'BACKGROUND';
            }

        // check music filesize
        } else if (content == 'audio') {
            max_filesize = MAX_MUSIC_FILESIZE;
            file_type    = 'MUSIC';
        }

        if (file.size > max_filesize * 1024 * 1024) {
            error_msg = 'TOO LARGE ' + file_type + ' (MAX ' + max_filesize + ' MiB)';
        }

        if (content == 'audio' && $('#musicslots').children().length == MAX_MUSIC_SLOTS) {
            showError('QUEUE FULL, RIGHT-CLICK SLOT TO CLEAR');
        }
    });

    if (error_msg != '') {
        notifyUploadFinish();
        showError(error_msg);
        return;
    }

    // upload files
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

            response = JSON.parse(response);

            // load images if necessary
            if (response['urls'].length > 0) {
                $.each(response['urls'], function(index, url) {
                    loadImage(url);
                });
                
                // trigger token creation via websocket
                writeSocket({
                    'OPID' : 'CREATE',
                    'posx' : mouse_x,
                    'posy' : mouse_y,
                    'size' : default_token_size,
                    'urls' : response['urls']
                });
            }

            if (response['music'].length > 0) {
                if (response['music'][0] == null) {
                    // notify full slots
                    showError('QUEUE FULL, RIGHT-CLICK SLOT TO CLEAR');
                    
                } else {
                    // broadcast music upload
                    writeSocket({
                        'OPID'   : 'MUSIC',
                        'action' : 'add',
                        'slots'  : response['music']
                    });
                }
            }
            
            notifyUploadFinish();
        }, error: function(response, msg) {
            notifyUploadFinish();
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

var token_icons = ['Rotate', 'Top', 'Delete', 'Bottom', 'Label', 'Resize', 'FlipX', 'Clone', 'Lock'];

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

        // padding avoids icons out of clickable range (especially
        // at the top, versus the GM's dropdown)
        var padding = 20;

        var icons = [token_icons];
        var isInt = token.text.startsWith('#') || (!isNaN(token.text) && token.text != '');
            
        if (isInt) {
            icons.push(['LabelInc', 'LabelDec']);
        }
        
        $.each(icons, function(i, use_icons) {
            $.each(use_icons, function(index, name) { 
                // calculate position based on angle
                var degree = 360.0 / use_icons.length;
                var s = Math.sin((-index * degree) * 3.14 / 180);
                var c = Math.cos((-index * degree) * 3.14 / 180);
                
                var radius = size * 0.7 * canvas_scale;
                if (i == 1) {
                    // shrink radius for inner icons
                    radius *= 0.5;
                }
                if(/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
                    // make tokenbar radius larger on mobile
                    radius *= 1.1;
                }
                var icon_x = x - radius * s;
                var icon_y = y - radius * c;
                
                // force position to be on the screen
                icon_x = Math.max(padding, Math.min(canvas.width()  - padding, icon_x));
                icon_y = Math.max(padding, Math.min(canvas.height() - padding, icon_y));
                
                // place icon
                var icon = $('#token' + name);
                var w = icon.width();
                var h = icon.height();
                icon.css('left', icon_x - w / 2 + 'px');
                icon.css('top',  icon_y - h / 2 + 'px');
            });
        });
        
        // handle locked mode
        if (token.locked) {
            $('#tokenFlipX').css('visibility', 'hidden');
            $('#tokenLock')[0].src = '/static/locked.png';
            $('#tokenTop').css('visibility', 'hidden');
            $('#tokenBottom').css('visibility', 'hidden');
            $('#tokenResize').css('visibility', 'hidden');
            $('#tokenRotate').css('visibility', 'hidden');
            $('#tokenClone').css('visibility', 'hidden');
            $('#tokenDelete').css('visibility', 'hidden');
            $('#tokenLabel').css('visibility', 'hidden');
            $('#tokenLabelDec').css('visibility', 'hidden');
            $('#tokenLabelInc').css('visibility', 'hidden');
        } else {
            $('#tokenFlipX').css('visibility', '');
            $('#tokenLock')[0].src = '/static/unlocked.png';
            $('#tokenTop').css('visibility', '');
            $('#tokenBottom').css('visibility', '');
            $('#tokenResize').css('visibility', '');    
            $('#tokenRotate').css('visibility', ''); 
            $('#tokenClone').css('visibility', '');
            $('#tokenDelete').css('visibility', '');
            $('#tokenLabel').css('visibility', '');

            var isInt = token.text.startsWith('#') || (!isNaN(token.text) && token.text != '');
            
            if (isInt) {
                $('#tokenLabelDec').css('visibility', '');
                $('#tokenLabelInc').css('visibility', '');
            } else {
                $('#tokenLabelDec').css('visibility', 'hidden');
                $('#tokenLabelInc').css('visibility', 'hidden');
            }
        }
    }
}

// ----------------------------------------------------------------------------

/// Select mouse/touch position relative to the screen
function pickScreenPos(event) {
    if ((event.type == "touchstart" || event.type == "touchmove") && event.touches.length == 1) {
        var touchobj = event.touches[0];
        var x = touchobj.clientX;
        var y = touchobj.clientY;
    } else {
        var x = event.clientX;
        var y = event.clientY;
    }

    return [x, y]
}

var mouse_delta_x = 0;
var mouse_delta_y = 0;

/// Select mouse/touch position relative to the canvas
function pickCanvasPos(event) {
    var old_x = mouse_x;
    var old_y = mouse_y;
    
    var p = pickScreenPos(event);
    mouse_x = p[0];
    mouse_y = p[1];
    
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

    mouse_delta_x = mouse_x - old_x;
    mouse_delta_y = mouse_y - old_y;
}

/// Event handle for pinging with the mouse (left click held)
function onDoubleClick() {
    writeSocket({
        'OPID' : 'BEACON',
        'x'    : mouse_x,
        'y'    : mouse_y
    });
}

/// Event handle for start grabbing a token
function onGrab(event) {
    event.preventDefault();
    closeGmDropdown();
    
    pickCanvasPos(event);
    if (!space_bar && event.buttons != 4) {
        // reset "user was scrolling" memory
        was_scrolled = false;
    }

    var is_single_touch = event.type == "touchstart" && event.touches.length == 1;
    var is_pinch_touch  = event.type == "touchstart" && event.touches.length == 2;
    if (is_pinch_touch) {
        touch_start = calcPinchCenter();
        pinch_distance = calcPinchDistance();
        return;
    } else if (is_single_touch) {
        touch_start = [mouse_x, mouse_y];
        touch_force = event.touches[0].force;
    }
    
    if (event.buttons == 1 || is_single_touch) {
        // trigger check for holding the click
        now = Date.now();
        var time_delta = now - initial_click;
        initial_click = now;
        if (time_delta <= double_click_limit) {
            onDoubleClick();
        }
        
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
            if (event.ctrlKey || event.metaKey) {
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
            $('#battlemap').css('cursor', 'move');
    
            var modified = false;

            if (event.ctrlKey || event.metaKey) {
                // toggle token in/out selection group
                var index = select_ids.indexOf(token.id);
                if (index != -1) {
                    // remove from selection
                    select_ids.splice(index, 1);
                } else {
                    // add to selection
                    select_ids.push(token.id);
                }
                primary_id = select_ids[0];
                modified   = true;
                
            } else {
                // reselect only if token wasn't selected before
                if (!select_ids.includes(token.id)) {
                    select_ids = [token.id];
                    primary_id = token.id;
                    
                } else {
                    primary_id = token.id;
                }
                modified = true;
                grabbed  = true;
            }

            if (modified) {
                // notify server about selection
                writeSocket({
                    'OPID'     : 'SELECT',
                    'selected' : select_ids
                });
            }
            
        } else if (!space_bar) {
            if (is_single_touch && !isExtremeForce(touch_force)) {
                // Clear selection
                select_ids = [];
                primary_id = 0;
            }

            // start selection box
            select_from_x = mouse_x;
            select_from_y = mouse_y;

            // immediately reset selection if strong touch
            // or if scrolling with spacebar
            // @NOTE: use a light gesture (e.g. pen) to select
            if (is_single_touch && isExtremeForce(event.touches[0].force)) {
                select_from_x = null;
                select_from_y = null; 
            }
        }
        
    } else if (event.buttons == 2 && !is_single_touch) {
        // Right click: reset token scale, flip-x & rotation
        var changes = [];
        $.each(select_ids, function(index, id) {
            var token = tokens[id];
            
            if (token.locked) {
                // ignore if locked
                return;
            }

            // reset rotation
            token.rotate = 0;

            // reset size to default size (but based on zoom)
            token.size   = parseInt(default_token_size / viewport.zoom);
            
            // trigger buffer redraw
            token.label_canvas = null;
            token.hue_canvas   = null;
            
            changes.push({
                'id'     : id,
                'size'   : token.size,
                'rotate' : token.rotate,
                'flipx'  : false
            });
        });
        
        writeSocket({
            'OPID'    : 'UPDATE',
            'changes' : changes
        });
    }
}

/// Event handle for releasing click/touch (outside canvas)
function onReleaseDoc() {
    if ((!space_bar || was_touch) && !was_scrolled) {
        if (select_from_x != null) {
            // range select tokens (including resetting selection)
            
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
            if (event.ctrlKey || event.metaKey) {
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
    }
    
    select_from_x = null;
    select_from_y = null;
}

/// Event handle for releasing a grabbed token
function onRelease() {
    var was_grabbed = grabbed;
    if (select_ids.length > 0) {
        grabbed = false;
        $('#battlemap').css('cursor', 'grab');
    }

    touch_force = 0.0;
    touch_start = null;
    var was_touch = event.type == "touchend";

    if (isNaN(mouse_x) || isNaN(mouse_y)) {
        // WORKAROUND: prevent mobile from crashing on pinch-zoom
        return;
    }

    if (primary_id > 0 && was_grabbed) {
        // finally push movement update to the server
        var changes = [];
        
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

function onMoveToken(event) {
    var token = tokens[primary_id];

    if (token == null || token.locked) {
        // skip: no primary token or it is locked
        return;
    }
    
    // transform cursor
    var battlemap = $('#battlemap');
    
    if (token == null) {
        battlemap.css('cursor', 'default');
    } else if (token.locked) {
        battlemap.css('cursor', 'not-allowed');
    } else if (grabbed) {
        battlemap.css('cursor', 'move');
    } else {
        battlemap.css('cursor', 'grab');
    }

    // move all selected tokens relative to the primary one
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

function onMoveViewport(dx, dy) {
    // change icon
    var battlemap = $('#battlemap');
    battlemap.css('cursor', 'grab');
    
    // NOTE: some browsers go crazy
    if (dx > 100) { dx /= 100; }
    if (dy > 100) { dy /= 100; }
    
    // move viewport
    viewport.newx = viewport.x + dx;
    viewport.newy = viewport.y + dy;

    was_scrolled = true;
}

function isExtremeForce(force) {
    return force == 0.0 || force == 1.0;
}

/// Event handle for moving mouse/finger
function onMove(event) {
    if (event.type == "touchmove") {
        // prevent scrolling
        event.preventDefault();
    }
    
    pickCanvasPos(event);

    var is_single_touch = event.type == "touchmove" && event.touches.length == 1;    
    var is_pinch_touch  = event.type == "touchmove" && event.touches.length == 2;

    if (is_pinch_touch) {
        // interpret pinch as zooming
        onWheel(event);
    
    } else if ((event.buttons == 1 && !space_bar) || is_single_touch) {
        // handle left click (without spacebar) or touch event
        if (primary_id != 0 && grabbed) {
            onMoveToken(event);
            
        } else if (is_single_touch) {
            if (isExtremeForce(touch_force)) {
                // only handle hard pressure (finger) as movement
                var dx = mouse_x - touch_start[0];
                var dy = mouse_y - touch_start[1];
                dx *= 3 / viewport.zoom;
                dy *= 3 / viewport.zoom;
                // @NOTE: move against drag direction
                onMoveViewport(-dx, -dy);
            }
        }
        
    } else if (event.buttons == 4 || (event.buttons == 1 && space_bar)) {
        // handle wheel click or leftclick (with space bar)
        // @NOTE: move against drag direction
        var dx = -event.movementX / viewport.zoom;
        var dy = -event.movementY / viewport.zoom;
        onMoveViewport(dx, dy);
               
    } else {                 
        // handle token mouse over
        var token = selectToken(mouse_x, mouse_y);
         
        // transform cursor
        var battlemap = $('#battlemap');
        if (token == null) {
            battlemap.css('cursor', 'default');
        } else if (token.locked) {
            battlemap.css('cursor', 'not-allowed');
        } else {                                         
            battlemap.css('cursor', 'grab');
        }
    }
}

var pinch_distance = null;

/// Calculate distance between fingers during pinch (two fingers)
function calcPinchDistance() {
    var x1 = event.touches[0].clientX;
    var y1 = event.touches[0].clientY;
    var x2 = event.touches[1].clientX;
    var y2 = event.touches[1].clientY;
    var dx = x1 - x2;
    var dy = y1 - y2;
    // @NOTE: sqrt is ignored here for gaining maximum speed
    return dx * dx + dy * dy;
}

/// Calculate center between fingers during pinch (two fingers)
function calcPinchCenter() {
    var x1 = event.touches[0].clientX;
    var y1 = event.touches[0].clientY;
    var x2 = event.touches[1].clientX;
    var y2 = event.touches[1].clientY;
    x = (x1 + x2) / 2;
    y = (y1 + y2) / 2;
    return [x, y];
}

/// Event handle mouse wheel scrolling
function onWheel(event) {  
    var speed = ZOOM_FACTOR_SPEED;   
    var delta = event.deltaY;
    
    // default: zoom using viewport's center
    var reference_x = viewport.x;
    var reference_y = viewport.y;
    if (delta < 0) {
        // zoom using mouse position
        reference_x = mouse_x;
        reference_y = mouse_y;
    }
    
    var is_pinch_touch  = event.type == "touchmove" && event.touches.length == 2;
    if (is_pinch_touch && pinch_distance != null) {
        // calculate pinch direction (speed is ignored!)
        var new_pinch_distance = calcPinchDistance();
        delta = pinch_distance - new_pinch_distance;
        if (Math.abs(delta) < 500) { // hardcoded threshold
            // ignore too subtle pinch
            return;
        }

        reference_x = touch_start[0];
        reference_y = touch_start[1];
        
        pinch_distance = new_pinch_distance;
    }
    
     if (event.ctrlKey || event.metaKey) {
        // ignore browser zoom
        return;
    }
    var show = false;
    var canvas = $('#battlemap');
    
    // modify zoom
    if (delta > 0) {
        // zoom out
        viewport.zoom /= speed;
        if (viewport.zoom < 1.0) {
            viewport.zoom = 1.0;
        }
        show = true;
    } else if (delta < 0) {
        // zoom in
        viewport.zoom *= speed;
        show = true;
    }

    // force all token labels to be redrawn
    $.each(tokens, function(index, token) {
        if (token != null) {
            token.hue_canvas = null;
        }
    });
    
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

var d100_queue = [];

/// Event handle to click a dice
function rollDice(sides) {
    // trigger dice shaking and poof (by re-applying CSS class)
    var target = $('#d' + sides + 'icon');
    var poofani = $('#d' + sides + 'poofani');      
    // @NOTE: delay required (else nothing will happen) 
    target.removeClass('shake').hide().delay(10).show().addClass('shake');
    poofani.removeClass('dicepoof').hide().delay(10).show().addClass('dicepoof');
    
    if (sides == 10) {
        if (d100_queue[0] != 10) {
            // bank d10 and schedule roll
            d100_queue.push(10);
            setTimeout(function() {  
                writeSocket({
                    'OPID'  : 'ROLL',
                    'sides' : d100_queue.shift()
                });
            }, 250);
        } else {
            // morph banked d10 into d100
            d100_queue[0] = 100;
        }
    } else {
        writeSocket({
            'OPID'  : 'ROLL',
            'sides' : sides
        });
    }
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

var viewport_scroll_delta = 50;

/// Event handle shortcuts on (first) selected token
function onShortcut(event) {
    space_bar = event.key == " ";

    // metaKey for Mac's Command Key
    if (event.ctrlKey || event.metaKey) {
        if (event.key.toLowerCase() == 'a') {
            selectAllTokens();
            
        } else if (event.key.toLowerCase() == 'c') {
            copySelectedTokens();
            
        } else if (event.key.toLowerCase() == 'v') {
            pasteCopiedTokens();
        }
    } else {
        // Backspace for MacBook's delete key
        if (event.key == 'Delete' || event.key == 'Backspace') {
            deleteSelectedTokens();
        }

        // handle movement of zoomed viewport
        // @NOTE: move with arrow direction
        if (event.key == 'ArrowUp') {
            onMoveViewport(0, -viewport_scroll_delta / viewport.zoom);
        }
        if (event.key == 'ArrowDown') {
            onMoveViewport(0, viewport_scroll_delta / viewport.zoom);  
        }
        if (event.key == 'ArrowLeft') {
            onMoveViewport(-viewport_scroll_delta / viewport.zoom, 0); 
        }
        if (event.key == 'ArrowRight') {
            onMoveViewport(viewport_scroll_delta / viewport.zoom, 0);  
        }
    }
}

/// Event handle for releasing a key
function onKeyRelease(event) {
    space_bar = false;
}

/// Event handle for fliping a token x-wise
function onFlipX() {
    event.preventDefault();
    
    var changes = [];
    $.each(select_ids, function(index, id) {
        var token = tokens[id];
        
        if (token == null || token.locked) {
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
    event.preventDefault();
    
    // determine primary lock state
    var primary_lock = false;
    if (primary_id > 0) {
        primary_lock = tokens[primary_id].locked
    }
    
    var changes = [];
    $.each(select_ids, function(index, id) {
        var token = tokens[id];
        token.locked = !primary_lock;

        // trigger buffer redraw
        token.label_canvas = null;
        token.hue_canvas   = null;
        
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
    event.preventDefault();
    
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

/// Event handle for changing a numeric token label
function onLabelStep(delta) {  
    event.preventDefault();
    
    var changes = [];
    var deleted = [];

    $.each(select_ids, function(index, id) {
        var token   = tokens[id];
        var isTimer = token.text.startsWith('#');
        var isInt   = isTimer || (!isNaN(token.text) && token.text != '');
            
        if (token == null || token.locked || !isInt) {
            // ignore if locked
            return;
        }
        // click token's number
        if (isTimer) {
            var number = parseInt(token.text.substr(1));
        } else {
            var number = parseInt(token.text);
        }
        number += delta;
        if (number <= 0) {
            number = 0;
        }
        if (isTimer) {
            token.text = '#';
        } else {
            token.text = '';
        }
        if (number > 0) {
            token.text += number;
        }
        
        // trigger buffer redraw
        token.label_canvas = null;
        token.hue_canvas   = null;

        if (number == 0 && isTimer) {
            deleted.push(id);
        } else {
            changes.push({
                'id'    : id,
                'text'  : token.text
            });
        }
    });
    
    writeSocket({
        'OPID'    : 'UPDATE',
        'changes' : changes
    });

    if (deleted.length > 0) {
        writeSocket({
            'OPID'   : 'DELETE',
            'tokens' : deleted
        });
    }
}

/// Event handle for entering a token label
function onLabel() {  
    event.preventDefault();
    
    if (select_ids.length == 0) {
        return;
    }
    
    var primary = tokens[select_ids[0]];
    var text = window.prompt('TOKEN LABEL (MAX LENGTH 15)', primary.text);
    if (text == null) {
        return;
    }

    // apply text
    text = text.substr(0, 15);
    var changes = [];

    $.each(select_ids, function(index, id) {
        var token = tokens[id];
        
        if (token.locked) {
            // ignore if locked
            return;
        }
        
        // move beneath lowest known z-order
        token.text  = text;
        
        // trigger buffer redraw
        token.label_canvas = null;
        token.hue_canvas   = null;
        
        changes.push({
            'id'    : id,
            'text'  : text
        });
    });
    
    writeSocket({
        'OPID'    : 'UPDATE',
        'changes' : changes
    });
}

/// Event handle for moving token to hightest z-order
function onTop() {  
    event.preventDefault();
    
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

/// Event handle for cloning the selected tokens
function onClone() {   
    event.preventDefault();
    
    // pick random position next to mouse
    var x = mouse_x + Math.floor(Math.random()*100) - 50;
    var y = mouse_y + Math.floor(Math.random()*100) - 50;
    
    writeSocket({
        'OPID' : 'CLONE',
        'ids'  : select_ids,
        'posx' : x,
        'posy' : y
    });
}
 
/// Event handle for deleting the selected tokens
function onTokenDelete() { 
    event.preventDefault();
    
    writeSocket({
        'OPID'   : 'DELETE',
        'tokens' : select_ids
    });
}

/// Event handle for start dragging a single dice container
function onStartDragDice(event, sides) {
    event.dataTransfer.setDragImage(drag_img, 0, 0);
    localStorage.setItem('drag_data',  sides);
    localStorage.setItem('drag_timer', '0');
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
    var is_drag_timer = localStorage.getItem('drag_timer');
    var sides = localStorage.getItem('drag_data');
    
    if (sides > 2 && is_drag_timer == '1') {
        
        // query last recent roll of that die by the current player
        if (sides == 2) {
            // ignore binary die
            return;
        }
        var key = sides + '_' + my_name;
        var r = sides; // fallback
        if (key in roll_history) {
            var r = roll_history[key];
        }

        // upload timer token to the game
        notifyUploadStart();

        // load transparent image from URL
        var img = new Image()
        img.src = '/static/token_d' + sides + '.png';
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
                    var data = JSON.parse(response);
                    $.each(data.urls, function(index, url) {
                        loadImage(url);
                    });
                    
                    // trigger token creation via websocket
                    writeSocket({
                        'OPID' : 'CREATE',
                        'posx' : mouse_x,  
                        'posy' : mouse_y,
                        'size' : default_token_size,
                        'urls' : data.urls,
                        'labels' : ['#' + r]
                    });
                    
                    notifyUploadFinish();
                }, error: function(response, msg) {
                    notifyUploadFinish();
                    handleError(response);
                }
            });
        };
    }
    
    localStorage.removeItem('drag_data');
    localStorage.removeItem('drag_timer');
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
        var pos = [window.innerWidth * 0.5, window.innerHeight - 1.5 * target.height()];
        
        // apply position
        movePlayersTo(pos);
        localStorage.removeItem('players');
    }
}
   
/// Event handle for stop dragging the players container
function onEndDragPlayers(event) {
    localStorage.removeItem('drag_data');
}

/// Event handle for start dragging the music tools container
function onStartDragMusic(event) {
    event.dataTransfer.setDragImage(drag_img, 0, 0);
    localStorage.setItem('drag_data', 'music');
}

/// Event handle for clicking the music tools container
function onResetMusic(event) {
    if (event.buttons == 2) {
        // reset music tools position
        var target = $('#musiccontrols');
        var x = window.innerWidth - target.width() * 1.75;
        var y = window.innerHeight * 0.5;
        
        // apply position
        moveMusicTo([x, y]);
        
        localStorage.removeItem('music');
    }
}
   
/// Event handle for stop dragging the players container
function onEndDragMusic(event) {
    localStorage.removeItem('drag_data');
}

/// Snaps dice container to the closest edge (from x, y)
function snapContainer(x, y, container, default_snap) {
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
}

function movePlayersTo(pos) {
    var target = $('#players'); 
    target.css('left', pos[0]);
    target.css('top',  pos[1]);
}

function moveMusicTo(pos) {
    var target = $('#musiccontrols');
    target.css('left', pos[0]);
    target.css('top',  pos[1]);
}

/// Check if die is dragged over screen border or not
function isDiceAtBorder() {
    var x = null;
    var y = null;
    
    if (event.type == 'touchmove') {
        // dragging dice on mobile
        x = event.touches[0].clientX;
        y = event.touches[0].clientY;
    } else {
        // dragging dice on desktop
        x = event.clientX;
        y = event.clientY;
    }

    // make position relative to screen
    x /= window.innerWidth;
    y /= window.innerHeight;

    var left_or_right = x < SCREEN_BORDER_WIDTH || x > 1 - SCREEN_BORDER_WIDTH;
    var top_or_bottom = y < SCREEN_BORDER_WIDTH || y > 1 - SCREEN_BORDER_WIDTH;
    
    return left_or_right || top_or_bottom
}

/// Drag dice container to position specified by the event
function onDragDice(event) {
    var is_drag_timer = localStorage.getItem('drag_timer');
    var sides = localStorage.getItem('drag_data');
    
    if (sides == 2 || isDiceAtBorder()) {
        localStorage.setItem('drag_timer', '0');
        
        // move die around edge
        var p = pickScreenPos(event);

        // drag dice box
        var target = $('#d' + sides + 'icon');

        // limit position to the screen
        var w = target.width();
        var h = target.height();
        var x = Math.max(0, Math.min(window.innerWidth - w,  p[0] - w / 2));
        var y = Math.max(0, Math.min(window.innerHeight - h, p[1] - h / 2));
        var data = [x, y];
        data = snapContainer(data[0], data[1], target, '');

        // apply position
        moveDiceTo(data, sides);
        saveDicePos(sides, data);
        
    } else {
        if (is_drag_timer == '0') {
            showTip('DROP TO ADD TO SCENE');
            localStorage.setItem('drag_timer', '1');
        }
    }
}

/// Drag players container to position specified by the event
function onDragPlayers(event) {
    var p = pickScreenPos(event);
    var target = $('#players');
    
    // limit position to the screen
    var w = target.width();
    var h = target.height();
    var x = Math.max(w / 2, Math.min(window.innerWidth - w/2, p[0]));
    var y = Math.max(0,     Math.min(window.innerHeight - h,  p[1]));
    var pos = [x, y];
    
    movePlayersTo(pos);
    savePlayersPos(pos);
}

/// Drag music tools container to position specified by the event
function onDragMusic(event) {
    var p = pickScreenPos(event);
    var target = $('#musiccontrols');

    // limit position to the screen
    var w = target.width();
    var h = target.height();
    var x = Math.max(0, Math.min(window.innerWidth - 2 * w, p[0]));
    var y = Math.max(h/2, Math.min(window.innerHeight - h/2,  p[1]));
    var pos = [x, y];
    
    moveMusicTo(pos);
    saveMusicPos(pos);
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
function onWindowResize(event) {
    // refresh default dice positions
    var total_dice_height = 50 * 7; // 7 dice
    var starty = window.innerHeight / 2 - total_dice_height / 2;

    if(/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {  
        // widely spread aligment on mobile
        default_dice_pos[20] = [15, window.innerHeight * 0.115, 'left'];
        default_dice_pos[12] = [15, window.innerHeight * 0.230, 'left'];
        default_dice_pos[10] = [15, window.innerHeight * 0.345, 'left'];
        default_dice_pos[ 8] = [15, window.innerHeight * 0.460, 'left'];
        default_dice_pos[ 6] = [15, window.innerHeight * 0.575, 'left'];
        default_dice_pos[ 4] = [15, window.innerHeight * 0.690, 'left'];
        default_dice_pos[ 2] = [15, window.innerHeight * 0.805, 'left'];

    } else {
        // tightly packed aligment on desktop
        default_dice_pos[20] = [15, starty    , 'left'];
        default_dice_pos[12] = [15, starty+ 50, 'left'];
        default_dice_pos[10] = [15, starty+100, 'left'];
        default_dice_pos[ 8] = [15, starty+150, 'left'];
        default_dice_pos[ 6] = [15, starty+200, 'left'];
        default_dice_pos[ 4] = [15, starty+250, 'left'];
        default_dice_pos[ 2] = [15, starty+300, 'left'];
    }
    
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
    data = snapContainer(data[0], data[1], $('#d' + sides + 'icon'), data[2]);
    
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

/// Save music tools position to local storage using percentage values
function saveMusicPos(pos) {
    pos[0] /= window.innerWidth;
    pos[1] /= window.innerHeight;
    localStorage.setItem('music', JSON.stringify(pos));
}

/// Event handle for toggling auto movement
function onToggleAutoMove(event) {
    event.preventDefault();
    toggleAutoMove();
}

function toggleAutoMove(load=false) {
    /*
    if (load) {
        // load from browser's storage
        var raw = localStorage.getItem('allow_auto_movement');
        allow_auto_movement = JSON.parse(raw);
    } else {
        // toggle
        allow_auto_movement = !allow_auto_movement;
    }

    // show (un)locked
    if (allow_auto_movement) {
        $('#beamLock')[0].src = '/static/unlocked.png';
    } else {
        $('#beamLock')[0].src = '/static/locked.png';
    }

    // save to browser's storage
    var raw = JSON.stringify(allow_auto_movement);
    localStorage.setItem('allow_auto_movement', raw);
    */
}

function getBlobFromDataURL(url) {
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

function getImageBlob(img) {
    var tmp_canvas = document.createElement("canvas");
    tmp_canvas.width  = img.width;
    tmp_canvas.height = img.height;
    var ctx = tmp_canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);
    url = tmp_canvas.toDataURL("image/png");

    return getBlobFromDataURL(url);
}

function ignoreBackground() {
    // load transparent image from URL
    var img = new Image()
    img.src = '/static/transparent.png';
    img.onload = function() {
        var blob = getImageBlob(img);
        var f = new FormData();
        f.append('file[]', blob, 'transparent.png');

        // upload for current scene
        uploadBackground(gm_name, game_url, f);
    };
}
