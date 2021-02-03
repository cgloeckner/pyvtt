/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/

function registerGm(event) {
    event.preventDefault();
    
    var gmname = $('#gmname').val();
    
    $.ajax({
        type: 'POST',
        url:  '/vtt/join',
        dataType: 'json',
        data: {
            'gmname' : gmname
        },
        success: function(response) {     
            // wait for sanizized gm url (as confirm)
            if (response['url'] == null) {
                showError(response['error']);
                
                // shake input
                $('#gmname').addClass('shake');
                setTimeout(function() {    $('#gmname').removeClass('shake'); }, 1000);
                
            } else {
                // redirect
                window.location = '/';
            }
        }, error: function(response, msg) {
            handleError(response);
        }
    });
}

function kickPlayers(url) {
    var kick = confirm("KICK ALL PLAYERS?");
    if (kick) {
        $.post(url='/vtt/kick-players/' + url);
    }
}

function kickPlayer(url, uuid) {
    var kick = confirm("KICK THIS PLAYER?");
    if (kick) {
        $.post(url='/vtt/kick-player/' + url + '/' + uuid);
    }
}

function deleteGame(url) {
    $.post(
        url='/vtt/delete-game/' + url,
        success=function(data) {
            $('#gmdrop')[0].innerHTML = data;
        }
    );
}

function fancyUrl() {
    // ask server to create nonsense game name
    $.get(
        url='/vtt/fancy-url',
        success=function(data) {
            $('#url').val(data);
        }
    );
}

function GmUploadDrag(event) {
    event.preventDefault();
}

function GmUploadDrop(event, url_regex, gm_url, max_zip, max_background) {
    event.preventDefault();
    
    showInfo('LOADING');
    
    // test upload data sizes
    var queue = $('#uploadqueue')[0];
    queue.files = event.dataTransfer.files;
    var sizes_ok = true;
    if (queue.files.length != 1) {   
        showError('USE A SINGLE FILE');
        return;
    }
    var max_filesize = max_background;
    var file_type    = 'BACKGROUND';
    if (queue.files[0].name.endsWith('.zip')) {
        max_filesize = max_zip;
        file_type    = 'GAME';
    }
    if (queue.files[0].size > max_filesize * 1024 * 1024) {
        showError('TOO LARGE ' + file_type + ' (MAX ' + max_filesize + ' MiB)');
        return;
    }
    
    // fetch upload data
    var f = new FormData($('#uploadform')[0]);

    tryGameCreation(f, url_regex);
}

function tryGameCreation(f, url_regex) {
    // test target game url
    var url = $('#url').val();
    if (url != '') {
        // check url via regex
        r = new RegExp(url_regex, 'g');
        if (!r.test(url)) { 
            showError('NO SPECIAL CHARS OR SPACES');
            
            // shake URL input
            $('#url').addClass('shake');
            setTimeout(function() {    $('#url').removeClass('shake'); }, 1000);
            return;
        }
    }
    
    // import game
    $.ajax({
        url: '/vtt/import-game/' + url,
        type: 'POST',
        data: f,
        contentType: false,
        cache: false,
        processData: false,
        success: function(response) {
            url_ok  = response['url_ok'];
            file_ok = response['file_ok'];
            
            if (!url_ok) {
                showError(response['error']);
                
                // shake URL input
                $('#url').addClass('shake');
                setTimeout(function() {    $('#url').removeClass('shake'); }, 1000);
                
            } else {
                if (!file_ok) { 
                    showError(response['error']);
                    
                    // reset uploadqueue
                    $('#uploadqueue').val("");
                    
                    // reset and shake URL input
                    $('#dropzone').addClass('shake');
                    setTimeout(function() {    $('#dropzone').removeClass('shake'); }, 1000);
                
                } else {
                    // load game
                    $('#popup').hide();
                    window.location = '/' + response['url'];
                }
            }
        }, error: function(response, msg) {
            handleError(response);
        }
    });
}

function GmQuickStart(url_regex) {
    showInfo('LOADING');

    // load transparent image from URL
    var img = new Image()
    img.src = '/static/transparent.png';
    img.onload = function() {
        var blob = getImageBlob(img);
        var f = new FormData();
        f.append('file', blob, 'transparent.png');

        tryGameCreation(f);
    };
}


// --- GM ingame tokenbar handles -------------------------------------

function reloadScenesDropdown() { 
    showInfo('Loading');
    $('#gmdrop')[0].innerHTML = '';
    $.post(
        url='/vtt/query-scenes/' + game_url,
        success=function(data) {          
            $('#popup').hide();
            $('#gmdrop')[0].innerHTML = data;
        }
    );
}

function addScene() {
    writeSocket({
        'OPID'  : 'GM-CREATE'
    });
    reloadScenesDropdown();
}

function activateScene(scene_id) {
    writeSocket({
        'OPID'  : 'GM-ACTIVATE',
        'scene' : scene_id
    });     
    reloadScenesDropdown();
}

function cloneScene(scene_id) {                                                                  
    writeSocket({
        'OPID'  : 'GM-CLONE',
        'scene' : scene_id
    });
    reloadScenesDropdown();
}

function deleteScene(scene_id) {
    writeSocket({
        'OPID'  : 'GM-DELETE',
        'scene' : scene_id
    });  
    reloadScenesDropdown();
}
