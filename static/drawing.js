function initDrawing() { 
    closeWebcam();

    // erase canvas
    var canvas = $('#doodle')[0];
    var context = canvas.getContext("2d");
    context.fillStyle = '#FFFFFF';
    context.fillRect(0, 0, canvas.width, canvas.height);

    $('#drawing').fadeIn(500);
}

function closeDrawing() {
    $('#drawing').fadeOut(500);
}

var pen_pos = [];

function onMovePen(event) {
    var use_pen = $('#penenable')[0].checked;
    
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

    pen_pos.push([x, y]);
}

function onReleasePen(event) {
    var canvas = $('#doodle')[0];
    var context = canvas.getContext("2d");

    console.log(pen_pos);

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
    console.log('up');
}

/*



function onStreamReady(stream) {
    window.stream = stream;
    $('#video')[0].srcObject = stream;
    $('#camerapreview').fadeIn(500);
    
    $('#applySnapshot').hide();
}

function onTakeSnapshot() {
    // apply video resolution to canvas
    var preview = $('#snapshot')[0]
    preview.width  = webcam_constraints.video.width;
    preview.height = webcam_constraints.video.height;

    // draw video snapshot onto canvas
    var context = preview.getContext('2d');
    context.clearRect(0, 0, preview.width, preview.height);
    context.drawImage($('#video')[0], 0, 0, preview.width, preview.height);
    
    $('#applySnapshot').fadeIn(100);
}

function onApplyBackground() {
    showInfo('LOADING');
    
    // fetch JPEG-data from canvas
    var preview = $('#snapshot')[0]
    var url = preview.toDataURL("image/jpeg");

    // prepare upload form data
    var blob = getBlobFromDataURL(url);
    var f = new FormData();
    f.append('file[]', blob, 'snapshot.jpeg');

    // upload for current scene
    uploadBackground(gm_name, game_url, f);
}

function closeWebcam() {
    $('#camerapreview').fadeOut(500);
    
    $('#video')[0] = null;
    window.stream  = null;    
    var preview = $('#snapshot')[0];
    var context = preview.getContext('2d');
    context.clearRect(0, 0, preview.width, preview.height);
}

function togglePreview(id) {
    var target = $(id);
    if (target.hasClass('largepreview')) {
        // reset to preview
        target.removeClass('largepreview');
        target.css('height', 180);
    } else {
        // enlarge
        target.addClass('largepreview');
        target.css('width', 'auto');
        target.css('height', window.innerHeight - 100);
    }
}

*/
