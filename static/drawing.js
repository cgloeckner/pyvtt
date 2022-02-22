var doodle_on_background = true;

function initDrawing(as_background) {
    // may fail if player draws
    try {
        closeWebcam();
    } catch {}

    doodle_on_background = as_background;

    var canvas = $('#doodle')[0];
    var context = canvas.getContext("2d");

    if (as_background) {
        // query background token
        var background = null;
        $.each(tokens, function(index, token) {
            if (token != null) {
                if (token.size == -1) {
                    background = token;
                    console.log(token);
                }
            }
        });
    }

    context.fillStyle = '#FFFFFF';
    context.fillRect(0, 0, canvas.width, canvas.height);
    
    if (as_background && background != null && images[background.url] != null) {
        // load background into canvas
        var sizes = getActualSize(background, canvas.width, canvas.height);
        sizes[0] *= canvas_scale;
        sizes[1] *= canvas_scale;
        
        
        context.drawImage(
            images[background.url],
            0.5 * canvas.width - sizes[0] / 2,
            0.5 * canvas.height - sizes[1] / 2,
            sizes[0], sizes[1]);
    
    }

    $('#drawing').fadeIn(500);
}

function closeDrawing() {
    $('#drawing').fadeOut(500);
}

var pen_pos = [];

function onMovePen(event) { 
    event.preventDefault();
    
    var use_pen = $('#penenable')[0].checked;
    var pressure = 1.0;
    
    if (event.type == "touchstart" || event.type == "touchmove") {
        // search all touches to use pen primarily
        var found = event.touches[0]; // fallback: 1st touch
        if (use_pen) {
            found = null;
        }
        for (var i = 0; i < event.touches.length; ++i) {
            if (!isExtremeForce(event.touches[i].force)) {
                // found sensitive input, ignore previously found event
                found = event.touches[i];
                //pressure = Math.sqrt(found.force);
                // @NOTE: pressure isn't working with a single path of lines (which uses a single width not handling multiple)
                use_pen = true;
                break;
            } 
        }
        event = found;
        
    } else if (event.buttons != 1) {
        event = null;
    }

    if (event == null) {
        // ignore
        return;
    }

    $('#penenable')[0].checked = use_pen;
    
    var canvas = $('#doodle')[0];
    var context = canvas.getContext("2d");

    // get mouse position with canvas (and consider hardcoded zoom)
    var box = canvas.getBoundingClientRect();
    var x = (event.clientX - box.left) * 2;
    var y = (event.clientY - box.top) * 2;

    if (pen_pos.length > 0) {
        var n = pen_pos.length;
        var width = parseInt($('#penwidth')[0].value);
        var color = $('#pencolor')[0].value;
        
        // preview next line segment
        context.strokeStyle = color;
        context.fillStyle = color;
        context.lineWidth = width;
        context.lineCap = "round";
        
        context.beginPath();
        context.moveTo(pen_pos[n-1][0], pen_pos[n-1][1]);
        context.lineTo(x, y);
        context.stroke();
    }

    pen_pos.push([x, y, pressure]);
}

function onReleasePen(event) { 
    event.preventDefault();
    
    var canvas = $('#doodle')[0];
    var context = canvas.getContext("2d");

    if (pen_pos.length > 1) { 
        // redraw entire line smoothly
        context.beginPath();       
        for (var i = 0; i < pen_pos.length; ++i) {
            if (i == 0) {
                context.moveTo(pen_pos[i][0], pen_pos[i][1]);
            } else {
                context.lineTo(pen_pos[i][0], pen_pos[i][1]);
            }
        }
        context.stroke();
        
    } else if (pen_pos.length == 1) {
        // draw dot
        context.beginPath();        
        context.moveTo(pen_pos[0][0], pen_pos[0][1]);
        context.lineTo(pen_pos[0][0]+1, pen_pos[0][1]+1);
        context.stroke();
    }
    
    pen_pos = [];
}

function onUploadDrawing() {
    notifyUploadStart();
    
    // fetch JPEG-data from canvas
    var preview = $('#doodle')[0];
    var url = preview.toDataURL("image/jpeg");

    // prepare upload form data
    var blob = getBlobFromDataURL(url);
    var f = new FormData();
    f.append('file[]', blob, 'snapshot.jpeg');

    if (doodle_on_background) {
        // upload for current scene
        uploadBackground(gm_name, game_url, f);
        
    } else {
        // upload as token at screen center
        var x = Math.round(MAX_SCENE_WIDTH / 2)
        var y = Math.round(MAX_SCENE_HEIGHT / 2);
        uploadFiles(gm_name, game_url, f, [], x, y);
    }

    closeDrawing();
}

