/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
*/

var gm   = '';
var game = '';

var num_slots = 0;

const volume_scale = 0.25;

/// Set music volume to audio object
function setAudioVolume(audio, volume) {
    audio.volume = volume * volume_scale;
}

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
        var div_events = 'onClick="onToggleMusicSlot(' + slot_id + ');" onContextMenu="onRemoveMusicSlot(' + slot_id + ');"';
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
function onToggleMusicSlot(slot_id) {
    var player = $(`#audioplayer${slot_id}`)[0];

    // check if track was already selected
    var action = 'play';
    if (!player.paused) {
        action = 'pause';
    }
    
    writeSocket({
        'OPID'    : 'MUSIC',
        'action'  : action,
        'slot_id' : slot_id
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
            'OPID'    : 'MUSIC',
            'action'  : 'remove',
            'slot_id' : slot_id
        });

        if (num_slots == 0) {
            $('#musiccontrols').hide(1000);
        }
    }
}

/// Play a music slot
function playMusicSlot(slot_id, update_id) {
    var player = $(`#audioplayer${slot_id}`);
    var was_paused = player.paused;

    // update player
    $('#musicStatus').hide();
    player.on('canplay', function() {  
        $('#musicStatus').show();

        let volume = parseFloat(localStorage.getItem('volume'))
        player.animate({volume: volume * volume_scale}, 1000)
        player[0].play();
        updateMusicUi();
    })
    player[0].src = '/asset/' + gm + '/' + game + '/' + slot_id + '.mp3?update=' + update_ids[slot_id];

}

function updateMusicUi() {
    // handle UI highlighting and count actual playbacks
    var num_playing = 0
    for (var n = 0; n < MAX_MUSIC_SLOTS; ++n) {
        var player = $(`#audioplayer${n}`)[0] 
        var slot = $(`#musicslot${n}`)  
        var playbackShown = slot.hasClass('playback')

        if (!player.paused) { // is playing
            num_playing += 1

            if (!playbackShown) {
                slot.addClass('playback')
            }
        } else {
            if (playbackShown) {
                slot.removeClass('playback')
            }
        }
    }
    
    // update volume UI
    var raw_volume = parseFloat(localStorage.getItem('volume'))
    var vol_str = parseInt(raw_volume * 100) + '%'
    if (num_playing == 0 || raw_volume == 0.0) {
        vol_str = '<img src="/static/muted.png" class="icon" />';
    }
    $('#musicvolume')[0].innerHTML = vol_str;

    // save current volume
    localStorage.setItem('volume', raw_volume);
}

/// Pause a music slot
function pauseMusic(slot_id) {       
    var player = $(`#audioplayer${slot_id}`);
    
    // fade and pause player
    let slot = $(`#musicslot${slot_id}`)
    player.animate({volume: 0}, 1000, function() {
        player[0].pause()
        updateMusicUi();
    })
}

/// Remove a music slot
function removeMusicSlot(slot_id) {
    $(`#musicslot${slot_id}`).remove()
    $(`#audioplayer${slot_id}`)[0].pause()
    update_ids[slot_id] = null;
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
    // modify volume
    let raw_volume = parseFloat(localStorage.getItem('volume'))
    let delta = getMusicVolumeDelta(raw_volume)
    raw_volume += direction * delta
    raw_volume = Math.round(raw_volume * 100) / 100.0

    // lock volume to [0.0; 1.0]
    if (raw_volume < 0.01) {
        raw_volume = 0.0
    } else if (raw_volume > 1.0) {
        raw_volume = 1.0
    }

    // adjust volume for all tracks
    for (var n = 0; n < MAX_MUSIC_SLOTS; ++n) { 
        var player = $(`#audioplayer${n}`)[0];
        setAudioVolume(player, raw_volume)
    }
    localStorage.setItem('volume', raw_volume)
    
    updateMusicUi();
}

function onInitMusicPlayer(gmurl, url) {    
    // setup audio source
    gm   = gmurl
    game = url

    // setup default volume
    var raw = localStorage.getItem('volume')
    if (!isNaN(raw)) {
        default_volume = parseFloat(raw)
    } else {
        default_volume = 0.10
        localStorage.setItem('volume', default_volume)
    }

    for (var n = 0; n < MAX_MUSIC_SLOTS; ++n) {
        var player = $(`#audioplayer${n}`)[0]
        setAudioVolume(player, default_volume)
    }
}
