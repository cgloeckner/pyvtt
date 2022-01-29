/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/

var gm   = '';
var game = '';

var playback = null;
var num_slots = 0;

/// Each slots has a timestamp assign indicating when it was set. This will help to ignore cache in case a music slot got updated
var update_ids = [];

/// Add a music slot
function addMusicSlot(slot_id) {
    if ($('#musiccontrols').css('display') == 'none') {
        $('#musiccontrols').show(1000);
    }
    
    if ($('#musicslot' + slot_id).length == 0) {
        // create container
        var div_id     = 'id="musicslot' + slot_id + '"';
        var div_title  = 'title="MUSIC SLOT ' + (slot_id+1) + '"';
        var div_events = 'onClick="onPlayMusicSlot(' + slot_id + ');" onContextMenu="onRemoveMusicSlot(' + slot_id + ');"';
        var container  = '<div class="slot" ' + div_id + ' ' + div_title + ' ' + div_events + '>' + (slot_id+1) + '</div>';
        
        // pick previous container
        var prev_id = parseInt(slot_id) - 1;
        var previous = $('#musicslot' + prev_id);
        if (slot_id == 0) {
            $('#musicslots').prepend(container);
        } else if (previous.length == 1) {
            $(container).insertAfter(previous);
        } else {
            $('#musicslots').append(container);
        }

        update_ids[slot_id] = Date.now();
        
        num_slots += 1;
    }
}

/// Event handle to play a music slot
function onPlayMusicSlot(slot_id) {
    var player = $('#audioplayer')[0];

    // check if track was already selected
    var action = 'play';
    if (slot_id == playback) {
        action = 'pause';
    }
    
    writeSocket({
        'OPID'   : 'MUSIC',
        'action' : action,
        'slot'   : slot_id
    });
}

/// Event handle for right clicking a music slot
function onRemoveMusicSlot(slot_id) {
    var fancy_slot = slot_id+1;
    switch (fancy_slot) {
        case 1:
            fancy_slot += 'ST';
            break;
        case 2:
            fancy_slot += 'ND';
            break;
        case 3:
            fancy_slot += 'RD';
            break;
        default:
            fancy_slot += 'TH';
    }
    if (confirm('CLEAR ' + fancy_slot + ' MUSIC SLOT?')) {
        num_slots -= 1;
        writeSocket({
            'OPID'   : 'MUSIC',
            'action' : 'remove',
            'slots'  : [slot_id]
        });

        if (num_slots == 0) {
            $('#musiccontrols').hide(1000);
        }
    }
}

/// Play a music slot
function playMusicSlot(slot_id, update_id) {
    var player = $('#audioplayer')[0];
    var was_paused = player.paused;

    // update player
    $('#musicStatus').hide();
    player.oncanplay = function(event) {  
        $('#musicStatus').show();
    };
    player.src = '/music/' + gm + '/' + game + '/' + slot_id + '/' + update_ids[slot_id];
    player.play();

    updateSlotHighlight(slot_id);
    updateMusicUi();
}

function updateSlotHighlight(slot_id) {
    if (playback != null) {
        $('#musicslot' + playback).removeClass('playback');
    }

    playback = slot_id;

    if (playback != null) {
        $('#musicslot' + playback).addClass('playback');
    }
}

function updateMusicUi() {   
    var player = $('#audioplayer')[0];
    
    // update play button and volume display
    var v = parseInt(player.volume * 100) + '%'
    if (player.paused || player.volume == 0.0) {
        v = '<img src="/static/muted.png" class="icon" />';
    }
    $('#musicvolume')[0].innerHTML = v;

    // save current volume
    localStorage.setItem('volume', player.volume);
}

/// Pause a music slot
function pauseMusic() {       
    var player = $('#audioplayer')[0];
    
    // pause player
    player.pause();

    updateSlotHighlight(null);
    updateMusicUi();
}

/// Remove a music slot
function removeMusicSlot(slot_id) {
    $('#musicslot' + slot_id).remove();

    if (playback == slot_id) {        
        playback = null;
        var player = $('#audioplayer')[0];
        player.pause();
        
        update_ids[slot_id] = null;
    }
}

/// Get delta for stepping music volume up or down, based on the current volume
function getMusicVolumeDelta(v) {
    if (v > 0.5) {
        return 0.1
    } else if (v > 0.25) {
        return 0.05;
    } else if (v > 0.1) {
        return 0.03
    } else {
        return 0.01;
    }
}

/// Change music volume
function onStepMusic(direction) {   
    var player = $('#audioplayer')[0];

    // modify volume
    var v = player.volume;
    delta = getMusicVolumeDelta(v);
    v += direction * delta;
    v = Math.round(v * 100) / 100.0;
    
    // fix bounding issues
    if (v < 0.01) {
        // stop playback
        v = 0.0;
        player.pause();
    } else if (v > 1.0) {
        // cap at 100%
        v = 1.0;
    }
    
    // continue playback if suitable
    if (v > 0.0 && player.paused && direction > 0) {
        player.play();
    }

    // apply volume
    player.volume = v;
    
    updateMusicUi();
}

function onInitMusicPlayer(gmurl, url) {
    // setup default volume
    var raw = localStorage.getItem('volume');
    if (raw != null) {
        default_volume = parseFloat(raw);
    } else {
        default_volume = 0.10;
    }

    // setup audio source
    gm   = gmurl;
    game = url;
    
    var player = $('#audioplayer')[0];
    player.volume = default_volume;
}
