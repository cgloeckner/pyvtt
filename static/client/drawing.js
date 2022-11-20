/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
*/

const gridsize = 32
const card_width  = 1600
const card_height = 1200
const token_size  = 900

var edges = []
var straight = null
var drag = null

var scale = 1.0
var index_card = new Image()
var token_img = new Image()
var token_background = new Image() 
var token_border = new Image()

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
    target.moveTo(line.x1 * card_width, line.y1 * card_height)
    target.lineTo(line.x2 * card_width, line.y2 * card_height)
    target.stroke();
}

function drawDot(x, y, color, width, target) {
    target.beginPath();
    target.strokeStyle = color
    target.fillStyle = color
    target.lineWidth = width
    target.arc(x * card_width, y * card_height, 1, 0, 2*Math.PI)
    target.stroke();
}

function drawAll(target) {
    // clear context   
    var canvas = $('#doodle')[0]
    target.clearRect(0, 0, canvas.width, canvas.height)
    target.lineCap = "round"

    let mode = localStorage.getItem('drawmode')

    if (mode == 'token') {
        // draw token image and border
        target.drawImage(token_background, 0, 0, token_size, token_size)
        
        target.globalCompositeOperation = 'source-atop'
        let x = token_size / 2
        let y = token_size / 2
        if (drag != null) {
            x = drag[0] * token_size
            y = drag[1] * token_size
        }
        target.drawImage(token_img,
            x - scale * token_img.width / 2,
            y - scale * token_img.height / 2,
            scale * token_img.width,
            scale * token_img.height)
        target.globalCompositeOperation = 'source-over'
        
        target.drawImage(token_border, 0, 0, token_size, token_size)
        
    } else {
        // load index card
        if (mode == 'card') {
            target.drawImage(index_card, 0, 0, card_width, card_height)
        }
        
        // draw all lines
        $.each(edges, function(index, data) {
            drawLine(data, target)
        })
    }
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

    index_card.src = '/static/index_card.jpg'
    token_background.src = '/static/token_background.png'
    token_border.src = '/static/token_border.png'

    onToggleMode(null)

    $('#drawing').fadeIn(500)
}

function onCloseDrawing() {
    $('#drawing').fadeOut(500)
}

function detectPressure(event) {
    // detect pen pressure
    let pressure = 1.0
    let use_pen = false

    if (event.type == "touchstart" || event.type == "touchmove") {
        // search all touches to use pen primarily
        var found = event.touches[0] // fallback: 1st touch
        // search for device that causes non-extreme pressure
        for (var i = 0; i < event.touches.length; ++i) {
            if (!isExtremeForce(event.touches[i].force)) {
                // found sensitive input, ignore previously found event
                found = event.touches[i]
                use_pen = true
                // @NOTE: pressure isn't working with a single path of lines (which uses a single width not handling multiple)
                pressure = parseInt(25 * event.touches[i].force)
                break
            }
        }
        event = found
    }

    if (use_pen) {
        // save pen pressure
        localStorage.setItem('draw_pressure', pressure)

    } else {
        // use last pen pressure
        pressure = localStorage.getItem('draw_pressure')
    }
    
    return pressure
}

function getDoodlePos(event) {
    // get mouse position with canvas (and consider hardcoded zoom) 
    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")

    var box = canvas.getBoundingClientRect()
    
    if (event.type == "touchstart" || event.type == "touchmove") {
        // use first touch event
        event = event.touches[0]
    }
    
    var x = (event.clientX - box.left) / box.width
    var y = (event.clientY - box.top) / box.height
    
    if (event.ctrlKey) {
        // snap to invisible grid
        x = gridsize * parseInt(x / gridsize)
        y = gridsize * parseInt(y / gridsize)
    }

    return [x, y]
}

function onMovePen(event) { 
    event.preventDefault()

    // redraw everything
    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")
    drawAll(context);
    
    var pos = getDoodlePos(event)

    if (!inTokenMode()) {
        // grab relevant data
        var width = detectPressure(event)
        var color = $('#pencolor')[0].value
        drawDot(pos[0], pos[1], color, width, context)
    }

    if (event.buttons == 1 || event.type == "touchstart" || event.type == "touchmove") {
        // drag mode
        if (!inTokenMode()) {
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
}

function onReleasePen(event) { 
    event.preventDefault()

    if (inTokenMode()) {
        if (token_img.src == '') {
            // upload token if not done yet
            $('#tokenupload')[0].click();
        }

        return
    }

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
}

function onChangeSize() {
    let slider = $('#token_scale')
    scale = slider[0].value / 100.0

    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")
    drawAll(context)
}

/// Modify line width using the mouse wheel
function onWheelPen(event) {
    var pressure = parseInt(localStorage.getItem('draw_pressure'))
    if (event.deltaY < 0) {
        pressure += 3
        if (pressure >= 100) {
            pressure = 100
        }
        /*scale *= 1.05
        if (scale > 10) {
            scale = 10
        }*/
    } else if (event.deltaY > 0) {
        pressure -= 3
        if (pressure <= 5) {
            pressure = 5
        }    
        /*scale /= 1.05
        if (scale < 0.1) {
            scale = 0.1
        }*/
    }
    localStorage.setItem('draw_pressure', pressure)
    
    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")
    drawAll(context)

    if (!inTokenMode()) {
        var pos = getDoodlePos(event)
        var color = $('#pencolor')[0].value
        drawDot(pos[0], pos[1], color, pressure, context)
    }
}

function onPrepareToken() {
    // test upload data sizes
    var file = $('#tokenupload')[0].files[0]
    error_msg = checkFile(file);

    if (error_msg != '') {
        showError(error_msg);
        return;
    }

    var filereader = new FileReader();
    filereader.readAsDataURL(file);

    filereader.onload = function(event) {
        token_img.onload = function() {
            let target = $('#doodle')
            $('#token_scale').show()

            let ctx = target[0].getContext("2d")
            drawAll(ctx)
        }

        token_img.src = filereader.result
    }
}

function onExportDrawing() {
    var preview = $('#doodle')[0];
    drawAll(preview.getContext("2d"))

    // fetch PNG-data from canvas
    var url = preview.toDataURL("image/png");

    let link  = document.createElement('a')
    link.href = url
    link.download = ''
    link.click()
}

function onUploadDrawing() {
    var preview = $('#doodle')[0];
    drawAll(preview.getContext("2d"))
    
    // fetch PNG-data from canvas
    var url = preview.toDataURL("image/png");

    // prepare upload form data
    var blob = getBlobFromDataURL(url);
    var f = new FormData();
    f.append('file[]', blob, 'snapshot.png');

    if (doodle_on_background) {
        // upload for current scene
        uploadBackground(gm_name, game_url, f);
        
    } else {
        // upload as token at screen center
        var x = Math.round(viewport.x)
        var y = Math.round(viewport.y)
        uploadFiles(gm_name, game_url, f, [], x, y);
    }

    onCloseDrawing();
}

function inTokenMode() {
    return localStorage.getItem('drawmode') == 'token'
}

function onToggleMode(mode=null) {
    let target = $('#doodle')

    let old_mode = localStorage.getItem('drawmode')
    if (mode == null) {
        mode = old_mode
    } else if (old_mode != null) {
        $(`#${old_mode}mode`).removeClass('border')
    }
    
    localStorage.setItem('drawmode', mode)
    $(`#${mode}mode`).addClass('border')

    if (mode == 'token') {
        // enable token mode
        target[0].width  = token_size
        target[0].height = token_size

        if (token_img.src != '') {
            $('#token_scale').show()
        } else {
            $('#token_scale').hide()
        }

    } else if (mode == 'card') {
        // enable index card mode
        target[0].width  = card_width
        target[0].height = card_height

        $('#token_scale').hide()

    } else {
        // enable overlay mode
        target[0].width  = card_width
        target[0].height = card_height 

        $('#token_scale').hide()
    }
    
    let ctx = target[0].getContext("2d")
    drawAll(ctx)
}

function onDropTokenImage(event) {
    if (!inTokenMode()) {
        return
    }
    
    let file = event.dataTransfer.files[0]
    error_msg = checkFile(file);

    if (error_msg != '') {
        showError(error_msg);
        return;
    }
    
    var filereader = new FileReader();
    filereader.readAsDataURL(file);
    
    filereader.onload = function(event) {
        token_img.onload = function() {
            let target = $('#doodle')
            $('#token_scale').show()

            let ctx = target[0].getContext("2d")
            drawAll(ctx)
        }

        token_img.src = filereader.result
    }
}
