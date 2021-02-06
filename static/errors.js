/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
*/

var show_hints = false;

function showPopup(msg, color, timeout, fadeout) {
    var popup = $('#popup');
    popup[0].innerHTML = msg;
    popup.css('color', color);
    popup.fadeIn(100, 0.0);
    if (timeout != null) {
        popup.delay(timeout).fadeOut(fadeout, 0.0);
    }
}
  
function showError(msg) {
    console.warn(msg);
    showPopup(msg, 'red', 7000, 3000);
}

function showInfo(msg) {
    showPopup(msg, 'white', null, null);
}

function showHint(event, msg) {
    if (!show_hints) {
        return;
    }
    
    var hint = $('#hint');
    hint[0].innerHTML = msg;
    /*
    hint.css('left', event.clientX);
    hint.css('top', event.clientY + 45);
    */
    hint.fadeIn(100, 0.0);
}

function hideHint() {
    var hint = $('#hint');
    hint.fadeOut(10, 0.0);
}

function handleError(response) {
    // parse error_id from response
    var error_id = response.responseText.split('<pre>')[1].split('</pre>')[0]
    
    // redirect to error page
    window.location = '/vtt/error/' + error_id;
}
