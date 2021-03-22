/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/

function showMusicVolume() {  
    var player = $('#audioplayer')[0];
    var v = parseInt(player.volume * 100) + '%'
    if (player.paused) {
        v = '<span class="muted">' + v + '</span>';
    }
    $('#volume')[0].innerHTML = v;
}

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
 
function setMusicVolume(v) {
    var player = $('#audioplayer')[0];
    player.volume = v;
    localStorage.setItem('volume', v);
    if (player.paused) {
        player.play();
    }
    showMusicVolume();
}
   
function onQuieterMusic() {
    var player = $('#audioplayer')[0];
    var v = player.volume;
    delta = getMusicVolumeDelta(v);
    v -= delta;
    if (v < 0.01) {
        v = 0.01;
    }
    setMusicVolume(v);
}

function onLouderMusic() {
    var player = $('#audioplayer')[0];
    var v = player.volume;
    delta = getMusicVolumeDelta(v);
    v += delta;
    if (v > 1.0) {
        v = 1.0;
    }
    setMusicVolume(v);
}

function onToggleMusic() { 
    var player = $('#audioplayer')[0];
    if (player.paused) {
        player.play();
    } else {
        player.pause();
    }
    showMusicVolume();
}

function onUpdateMusic() {
    var player = $('#audioplayer')[0];
    old_src = player.src;
    player.src = '';
    player.src = old_src;
    player.play();
}

function onInitMusicPlayer() {
    // setup default volume
    default_volume = localStorage.getItem('volume');;
    if (default_volume == null) {
        default_volume = 0.15;
    }
    var player = $('#audioplayer')[0];
    player.volume = default_volume;
}
