/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/

var socket = null; // websocket used for client-server-interaction
var quiet = true;

var ping_delay = 2000; // delay between two pings
var next_ping  = null; // indicates when the next ping will be sent
var last_ping  = null; // timestamp when last ping was sent

var socket_move_delay = 100;
var socket_move_timeout = 0; // delay until the next move update will be sent through the socket

// --- game state implementation ----------------------------------------------

var game_url = '';
var gm_name = '';
var gm_dropdown = false; // GM's scenes view
var history_dropdown = false; // roll history
var timeid = 0;
var full_update = true;
var scene_id = 0;
var is_gm = false;

var my_uuid = '';
var my_name = '';
var my_color = '';

/// Handle function for interaction via socket
function onSocketMessage(event) {
    var data = JSON.parse(event.data);
    var opid = data.OPID;
    
    if (!quiet) {
        console.info('READ', data);
    }
    
    switch (opid) { 
        case 'PING':
            onPing(data);
            break;
        case 'ACCEPT':
            onAccept(data);
            break;  
        case 'UPDATE':
            onUpdate(data);
            break;
        case 'CREATE':
            onCreate(data);
            break;
        case 'DELETE':
            onDelete(data);
            break;
        case 'REFRESH':
            onRefresh(data);
            break;
        case 'JOIN':
            onJoin(data);
            break;
        case 'QUIT':
            onQuit(data);
            break;
        case 'ROLL':
            onRoll(data);
            break;
        case 'SELECT':
            onSelect(data);
            break;
        case 'ORDER':
            onOrder(data);
            break;
        case 'BEACON':
            onBeacon(data);
            break;
        case 'MUSIC':
            onMusic(data);
            break;
        default:
            console.error('Invalid OpID "' + opid + '"');
    };
}

function onAccept(data) {
    // show all players
    $.each(data.players, function(i, details) {
        var p = new Player(details.name, details.uuid, details.color, details.ip, details.country, details.flag, details.index);
        p.is_last = p.index == data.players.length - 1;
        showPlayer(p);
    });
    
    // show all rolls
    $.each(data.rolls, function(item, obj) {
        addRoll(obj.sides, obj.result, obj.name, obj.color, obj.recent);
    });

    // cache all required assets
    $.each(data.urls, function(i, url) {
        loadImage(url);
    });

    // show music slots
    $.each(data.slots, function(i, slot) {
        addMusicSlot(slot);
    });
    if (data.playback != null) {
        playMusicSlot(data.playback);
    }
    
    onRefresh(data);
}

function onUpdate(data) {
    var is_primary = false;
    
    $.each(data.tokens, function(index, token) {
        updateToken(token);
        
        if (token.id == primary_id) {
            is_primary = true;
        }
    });
}

function onCreate(data) {
    $.each(data.tokens, function(index, token) {
        updateToken(token, true);
        
        tokens_added[token.id] = 0.0;
    });
}

function onDelete(data) {
    $.each(data.tokens, function(index, id) {
        // overwrite new position with current
        // (this will prevent from fading out at (0|0)
        var copy = tokens[id];
        copy.newx = copy.posx;
        copy.newy = copy.posy;

        delete tokens[id];
        
        tokens_removed[id] = [copy, 1.0];
    });
}

function onJoin(data) {
    var p = new Player(data.name, data.uuid, data.color, data.ip, data.country, data.flag, data.index);
    showPlayer(p);
}

function onQuit(data) {
    hidePlayer(data.uuid); 
}

function onRoll(data) {
    addRoll(data.sides, data.result, data.name, data.color, data.recent);
}

function onSelect(data) {
    player_selections[data.color] = data.selected;
    
    // update player's primary selection
    if (data.color == my_color && data.selected.length > 0) {
        select_ids = data.selected;
        if (!select_ids.includes(primary_id)) {
            // reselect primary item (previous one does not belong to new selection)
            primary_id = data.selected[0];
        }
    }
}

function onOrder(data) {
    $.each(data.indices, function(uuid, index) {
        players[uuid].index = index;
        players[uuid].is_last = index == Object.keys(data.indices).length - 1;
    });
    
    rebuildPlayers();
}

function onBeacon(data) {
    // grab beacon
    var beacon = beacons[data['uuid']];
    if (beacon == null) {
        addBeacon(data['color'], data['uuid']);
        beacon = beacons[data['uuid']];
    }
    
    // update beacon
    startBeacon(beacon, data['x'], data['y']);

    // move viewport towards beacon if zoomed in
    if (viewport.zoom > 1.0) {
        viewport.newx = data['x'];
        viewport.newy = data['y'];
    }
}

function onMusic(data) {
    switch (data['action']) {
        case 'play':
            playMusicSlot(data['slot']);
            break;

        case 'pause':
            pauseMusic();
            break;
            
        case 'add':
            $.each(data['slots'], function(index, slot) {
                if (slot != null) {
                    addMusicSlot(slot);
                }
            });
            break;

        case 'remove':
            $.each(data['slots'], function(index, slot) {
                removeMusicSlot(data['slots']);
            });
            break;
    }
}

function onRefresh(data) {
    resetViewport();
    
    // show drop hint again
    $('#draghint').show();
    
    // reset tokens               
    background_set = false;
    tokens = [];
    $.each(data.tokens, function(index, token) {
        updateToken(token, true);
    });
}

/// Send data JSONified to server via the websocket
function writeSocket(data) {
    var raw = JSON.stringify(data);
    if (!quiet) {
        console.info('SEND', data);
    }
    socket.send(raw);
}

/// Called after drawing to update ping if necessary
function updatePing() {
    var now = Date.now();
    if (now >= next_ping) {
        // trigger next ping
        next_ping = now + ping_delay;
        last_ping = now;
        writeSocket({'OPID': 'PING'});
    }
}

/// Event handle to react on server's ping reply
function onPing(data) {
    // calculate time since ping request
    var now   = Date.now();
    var delta = now - last_ping;
    $('#ping')[0].innerHTML = 'PING: ' + delta + 'ms';
}

/// Handle picking a random color
function pickRandomColor() {
    var index = Math.floor(Math.random() * SUGGESTED_PLAYER_COLORS.length);
    $('#playercolor')[0].value = SUGGESTED_PLAYER_COLORS[index];
}

/// Handles login and triggers the game
function login(event, gmname, url, websocket_url) {
    event.preventDefault();
    
    $('#popup').hide();
    
    var playername  = $('#playername').val();
    var playercolor = $('#playercolor').val();
    
    $.ajax({
        type: 'POST',
        url:  '/' + gmname + '/' + url + '/login',
        dataType: 'json',
        data: {
            'playername'  : playername,
            'playercolor' : playercolor
        },
        success: function(response) {
            // wait for sanitized input
            error       = response['error']
            playername  = response['playername']
            playercolor = response['playercolor']
            is_gm       = response['is_gm']
            my_uuid     = response['uuid']
            
            if (error != '') {
                showError(error);
                
                $('#playername').addClass('shake');
                setTimeout(function() {    $('#playername').removeClass('shake'); }, 1000);
                
            } else {
                $('#historydrop').hide();
                $('#loginbtn').hide();

                //$('#musiccontrols').hide();
                $('#game').fadeIn(500, 0.0, function() {
                    // show players
                    $('#mapfooter').css('display', 'block');
                    $('#mapfooter').animate({ opacity: '+=1.0' }, 1000);
                    
                    // show dice
                    $('#dicebox').css('display', 'block'); 
                    $('#dicebox').animate({ opacity: '+=1.0' }, 500);
                    
                    $('#version')[0].innerHTML = 'v' + version;
                    $('#musicStatus').hide();
                    
                    onWindowResize();
                });
                
                $('#login').fadeOut(500, 0.0, function() {
                    $('#login').hide();
                    $('#popup').hide();
                });
                
                resetViewport();
                
                // start socket communication
                socket = new WebSocket(websocket_url)
                
                socket.onmessage = onSocketMessage;
                
                socket.onopen = function() {
                    start(gmname, url, playername, playercolor);
                };
                
                socket.onclose = function(event) {
                    running = false;
                    
                    // reset audio
                    $('#audioplayer')[0].pause();
                    $('#musicslots')[0].innerHTML = ''
                    
                    $('#game').fadeOut(1000, 0.0);
                    
                    // forget everything about the old session
                    images            = [];
                    tokens            = [];
                    tokens_added      = [];
                    tokens_removed    = [];
                    player_selections = {};
                    culling           = [];
                    players           = {};
                    rolls             = []; 
                    copy_tokens       = [];
                    select_ids        = [];
                    is_gm             = false;
                    my_uuid           = '';
                    
                    last_dice_timeid  = 0;
                    last_dice_series  = null;
                    
                    $.each(dice_sides, function(index, sides) {
                        var d = $('#d' + sides + 'rolls');
                        d[0].innerHTML = '';
                    });
                    
                    // return to login screen     
                    $('#loginbtn').show();
                    $('#login').fadeIn(1000, 0.0, function() {
                        showError('CONNECTION LOST');
                    });
                };
            }
        }, error: function(response, msg) {
            if ('responseText' in response) {
                handleError(response);
            } else {
                showError('SERVER NOT FOUND');
            }
        }
    });
}

/// Sets up the game and triggers the update loop
function start(gmname, url, playername, color) {
    onInitMusicPlayer(gmname, url);
    toggleAutoMove(true);

    writeSocket({
        'name'     : playername,
        'gm_url'   : gmname,
        'game_url' : url
    });

    my_name = playername;
    my_color = color;
    
    // setup in-memory canvas (for transparency checking)
    mem_canvas = document.createElement('canvas');
    
    // disable window context menu for token right click
    document.addEventListener('contextmenu', event => {
        event.preventDefault();
    });
    
    // drop zone implementation (using canvas) --> also as players :) 
    document.addEventListener('dragover',    onDrag);
    document.addEventListener('drop',         onDrop);
    
    // desktop controls
    battlemap.addEventListener('mousedown',    onGrab);
    battlemap.addEventListener('touchstart',   onGrab);
    
    battlemap.addEventListener('mousemove',    onMove);
    battlemap.addEventListener('touchmove',    onMove);
    
    battlemap.addEventListener('mouseup',    onRelease);
    battlemap.addEventListener('touchend',    onRelease);
    
    battlemap.addEventListener('wheel',        onWheel);
    document.addEventListener('keydown',    onShortcut);
    document.addEventListener('keyup',        onKeyRelease);

    $(window).resize(onWindowResize);
    
    // setup game  
    gm_name = gmname;
    game_url = url;

    running = true;
    drawScene();
}
