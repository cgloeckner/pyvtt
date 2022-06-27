var doodle_on_background = true

var edges = []
var straight = null
var drag = null

/// Line constructor
function Line(x1, y1, x2, y2, width, color) {
    this.x1 = x1 
    this.y1 = y1
    this.x2 = x2
    this.y2 = y2
    this.width = width
    this.color = color
}

function drawLine(line, target) {
    if (line.x1 == null || line.x2 == null) {
        return;
    }
    target.beginPath();
    target.strokeStyle = line.color
    target.fillStyle = line.color
    target.lineWidth = line.width
    target.moveTo(line.x1, line.y1)
    target.lineTo(line.x2, line.y2)
    target.stroke();
}

function drawDot(x, y, color, width, target) {
    target.beginPath();
    target.strokeStyle = color
    target.fillStyle = color
    target.lineWidth = width
    target.arc(x, y, 1, 0, 2*Math.PI)
    target.stroke();
}

function drawAll(target) {
    // search for background token
    if (doodle_on_background) {
        // query background token
        var background = null
            $.each(tokens, function(index, token) {
            if (token != null) {
                if (token.size == -1) {
                    background = token
                }
            }
        });
    }

    // clear context
    var canvas = $('#doodle')[0]
    target.fillStyle = '#FFFFFF'
    target.fillRect(0, 0, canvas.width, canvas.height)
    target.lineCap = "round"

    // load background if necessary
    if (background != null && images[background.url] != null) {
        // load background into canvas
        var sizes = getActualSize(background, canvas.width, canvas.height)
        sizes[0] *= canvas_scale
        sizes[1] *= canvas_scale
        
        target.drawImage(
            images[background.url],
            0.5 * canvas.width - sizes[0] / 2,
            0.5 * canvas.height - sizes[1] / 2,
            sizes[0], sizes[1]
        )
    }

    // draw all lines
    $.each(edges, function(index, data) {
        drawLine(data, target)
    })
}

function initDrawing(as_background) {
    // may fail if player draws
    try {
        closeWebcam()
    } catch {}

    doodle_on_background = as_background

    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")
    
    edges = []
    straight = null
    drag = null
    drawAll(context)

    $('#drawing').fadeIn(500)
}

function closeDrawing() {
    $('#drawing').fadeOut(500)
}

function detectPressure(event) {
    // detect pen pressure
    var use_pen = $('#penenable')[0].checked
    var pressure = 1.0
    
    if (event.type == "touchstart" || event.type == "touchmove") {
        // search all touches to use pen primarily
        var found = event.touches[0] // fallback: 1st touch
        if (use_pen) {
            found = null
        }
        // search for device that causes non-extreme pressure
        // @NOTE: extreme pressure mostly indicates a mouse
        for (var i = 0; i < event.touches.length; ++i) {
            if (!isExtremeForce(event.touches[i].force)) {
                // found sensitive input, ignore previously found event
                found = event.touches[i]
                // @NOTE: pressure isn't working with a single path of lines (which uses a single width not handling multiple)
                use_pen = true
                break
            } 
        }
        event = found
    }
    $('#penenable')[0].checked = use_pen

    if (!use_pen) {
        pressure = parseInt(localStorage.getItem('draw_pressure'))
        if (isNaN(pressure)) {
            localStorage.setItem('draw_pressure', 20)
            pressure = 20
        }
        
        console.log('load from storage', pressure)
    } else {
        localStorage.setItem('draw_pressure', pressure)
        
        console.log('save to storage', pressure)
    }

    return pressure
}

function getDoodlePos(event) {
    // get mouse position with canvas (and consider hardcoded zoom) 
    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")

    var box = canvas.getBoundingClientRect()
    var x = (event.clientX - box.left) * 2
    var y = (event.clientY - box.top) * 2
    
    return [x, y]
}

function onMovePen(event) { 
    event.preventDefault()

    // redraw everything
    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")
    drawAll(context);

    // grab relevant data
    var width = detectPressure(event)
    var pos = getDoodlePos(event)
    var color = $('#pencolor')[0].value
    drawDot(pos[0], pos[1], color, width, context)

    if (event.buttons == 1) {
        // drag mode
        if (drag != null) { 
            straight = null
            
            // add segment
            var line = new Line(
                drag[0], drag[1],
                pos[0], pos[1],
                width, color
            )
            edges.push(line)
        }
        // continue dragging
        drag = pos
    
    } else if (event.shiftKey) {
        // straight line mode
        if (straight != null) {
            // update end point
            straight.x2 = pos[0]
            straight.y2 = pos[1]
            straight.width = width
            straight.color = color

            // redraw (including preview)
            var canvas = $('#doodle')[0]
            var context = canvas.getContext("2d")
            drawAll(context)
            drawLine(straight, context)
        }
    }
    
    /*
    // detect pen pressure
    var use_pen = $('#penenable')[0].checked
    var pressure = 1.0
    
    if (event.type == "touchstart" || event.type == "touchmove") {
        // search all touches to use pen primarily
        var found = event.touches[0] // fallback: 1st touch
        if (use_pen) {
            found = null
        }
        for (var i = 0; i < event.touches.length; ++i) {
            if (!isExtremeForce(event.touches[i].force)) {
                // found sensitive input, ignore previously found event
                found = event.touches[i]
                // @NOTE: pressure isn't working with a single path of lines (which uses a single width not handling multiple)
                use_pen = true
                break
            } 
        }
        event = found
        
    } else if (event.buttons != 1) {
        event = null
    }
    if (event == null) {
        // ignore
        return
    }
    $('#penenable')[0].checked = use_pen;
    */

    /*

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
    */
}

function onReleasePen(event) { 
    event.preventDefault()

    // grab some data
    var width = detectPressure(event)
    var color = $('#pencolor')[0].value
    var pos = getDoodlePos(event)

    // stop dragging
    drag = null

    if (event.shiftKey) {
        // straight mode:
        if (straight != null && straight.x2 != null) {
            // finish line
            straight.width = width
            straight.color = color
            edges.push(straight)

            // redraw
            var canvas = $('#doodle')[0]
            var context = canvas.getContext("2d")
            drawAll(context)
        }
        
    }
    // start new line
    straight = new Line(
        pos[0], pos[1],
        null, null,
        width, color
    )

    /*
    var canvas = $('#doodle')[0];
    var context = canvas.getContext("2d");
    
    // get mouse position with canvas (and consider hardcoded zoom)
    var box = canvas.getBoundingClientRect()
    var x = (event.clientX - box.left) * 2
    var y = (event.clientY - box.top) * 2
    
    if (event.shiftKey && line_from != null) {
        var width = parseInt($('#penwidth')[0].value);
        var color = $('#pencolor')[0].value;
        
        // draw straight line
        context.strokeStyle = color;
        context.fillStyle = color;
        context.lineWidth = width;
        context.lineCap = "round";
        
        context.beginPath()
        context.moveTo(line_from[0], line_from[1])
        context.lineTo(x, y)
        context.stroke()
    }
    line_from = [x, y];
    
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
    */
}

/// Modify line width using the mouse wheel
function onWheel(event) {
    var pressure = parseInt(localStorage.getItem('draw_pressure'))
    if (event.deltaY < 0) {
        pressure += 3
        if (pressure >= 100) {
            pressure = 100
        }
    } else if (event.deltaY > 0) {
        pressure -= 3
        if (pressure <= 5) {
            pressure = 5
        }
    }
    localStorage.setItem('draw_pressure', pressure)
    
    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")
    drawAll(context)

    var pos = getDoodlePos(event)
    var color = $('#pencolor')[0].value
    drawDot(pos[0], pos[1], color, pressure, context)
}

function onUploadDrawing() {
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

