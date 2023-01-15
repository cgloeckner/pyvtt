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
        let w = scale * token_img.width * token_size / token_img.width
        let h = scale * token_img.height * token_size / token_img.width
        target.drawImage(token_img,
            x - w / 2,
            y - h / 2,
            w,
            h)
        target.globalCompositeOperation = 'source-over'

        let hsl = getHsl($('#pencolor')[0].value)
        let filter = target.filter
        target.filter = `hue-rotate(${hsl[0]}turn) saturate(${hsl[1]}) brightness(${5*hsl[2]})`
        target.drawImage(token_border, 0, 0, token_size, token_size)
        target.filter = filter
        
    } else {
        // load index card
        if (mode == 'card') {
            target.fillStyle = '#FFFFFF'
            target.fillRect(0, 0, card_width, card_height)
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

    index_card.src = '/static/index_card.png'
    token_background.src = '/static/token_background.png'
    token_border.src = '/static/token_border.png'

    onToggleMode(null)

    $('#drawing').fadeIn(500)
}

function onCloseDrawing() {
    token_img.src = ''
    edges = []
    
    $('#drawing').fadeOut(500)
}

function detectPressure(event) {
    // detect pen pressure
    let pressure = event.pressure

    // @NOTE pointerType seems to default to 'touch' when using a pen
    //let use_pen  = event.pointerType == 'pen'

    // @NOTE not used right now (wheel-change disabled)
    //localStorage.setItem('draw_pressure', pressure)

    return pressure
}

function isPenPressure(pressure) {
    return pressure != 0.5 && pressure != 1.0
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
        drawDot(pos[0], pos[1], color, parseInt(25 * width), context)
    }

    if (event.buttons == 1) {
        // drag mode
        if (!inTokenMode()) {
            if (drag != null) { 
                straight = null
                
                // add segment
                var line = new Line(
                    drag[0], drag[1],
                    pos[0], pos[1],
                    parseInt(25 * width), color
                )
                edges.push(line)
            }
        }
        
        // continue dragging
        if (drag == null) {
            drag = pos
        } else {
            drag[0] += event.movementX * 0.001
            drag[1] += event.movementY * 0.001
        }
    
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
            straight.width = parseInt(25 * width)
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
        parseInt(25 * width), color
    )
}

function onUndo() {
    edges.pop()

    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")
    drawAll(context)
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
    /*
    var pressure = parseFloat(localStorage.getItem('draw_pressure'))
    if (event.deltaY < 0) {
        pressure += 0.1
        if (pressure >= 1.0) {
            pressure = 1.0
        }
    } else if (event.deltaY > 0) {
        pressure -= 0.1
        if (pressure <= 0.0) {
            pressure = 0.0
        }  
    }
    localStorage.setItem('draw_pressure', pressure)
    */
    
    var canvas = $('#doodle')[0]
    var context = canvas.getContext("2d")
    drawAll(context)

    if (!inTokenMode()) {
        var pos = getDoodlePos(event)
        var color = $('#pencolor')[0].value
        drawDot(pos[0], pos[1], color, parseInt(25 * pressure), context)
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
            $('#token_scale_box').show()

            let ctx = target[0].getContext("2d")
            drawAll(ctx)
        }

        token_img.src = filereader.result
    }
}

function onExportDrawing() {
    let mode = localStorage.getItem('drawmode')
    
    var preview = $('#doodle')[0];
    drawAll(preview.getContext("2d"))

    // fetch PNG-data from canvas
    var url = preview.toDataURL("image/png");

    let link  = document.createElement('a')
    link.href = url
    link.download = `${mode}.png`
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

function onPickColor() {
    let target = $('#doodle')
    let ctx = target[0].getContext("2d")
    drawAll(ctx)
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

    $('#pencolor')[0].value = '#000000'
    straight = null
    drag = null

    if (mode == 'token') {
        // enable token mode
        target[0].width  = token_size
        target[0].height = token_size

        if (token_img.src != '') {
            $('#token_scale_box').show()
        } else {
            $('#token_scale_box').hide()
        }

        $('#undo_button').hide()
        $('#pencolor')[0].value = '#FF0000'

    } else if (mode == 'card') {
        // enable index card mode
        target[0].width  = card_width
        target[0].height = card_height

        $('#token_scale_box').hide() 
        $('#undo_button').show()

    } else {
        // enable overlay mode
        target[0].width  = card_width
        target[0].height = card_height 

        $('#token_scale_box').hide() 
        $('#undo_button').show()
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
            $('#token_scale_box').show()

            let ctx = target[0].getContext("2d")
            drawAll(ctx)
        }

        token_img.src = filereader.result

        // reset position and scaling
        drag = null
        $('#token_scale')[0].value = 100

        onChangeSize()
    }
}
