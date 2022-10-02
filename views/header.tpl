<!--
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
//-->

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <link rel="shortcut icon" href="{{engine.adjustStaticsUrl('/static/favicon.ico?v=' + engine.version)}}" type="image/x-icon">
    <script src="{{engine.adjustStaticsUrl('/static/jquery-3.3.1.min.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/md5.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/version.js?v=' + engine.version)}}"></script>   
    <script src="{{engine.adjustStaticsUrl('/static/errors.js?v=' + engine.version)}}"></script>   
    <script src="{{engine.adjustStaticsUrl('/static/dropdown.js?v=' + engine.version)}}"></script>   
    <script src="{{engine.adjustStaticsUrl('/static/render.js?v=' + engine.version)}}"></script>  
    <script src="{{engine.adjustStaticsUrl('/static/ui.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/socket.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/gm.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/music.js?v=' + engine.version)}}"></script>    
    <script src="{{engine.adjustStaticsUrl('/static/utils.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/webcam.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/mobile-upload.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/drawing.js?v=' + engine.version)}}"></script>
    <script src="{{engine.adjustStaticsUrl('/static/constants.js?v=' + engine.version)}}"></script>
    <link rel="stylesheet" type="text/css" href="{{engine.adjustStaticsUrl('/static/normalize.css?v=' + engine.version)}}">
    <link rel="stylesheet" type="text/css" href="{{engine.adjustStaticsUrl('/static/layout.css?v=' + engine.version)}}">
    <title>{{engine.title}}: {{title}}</title>
    <style>
div.container {
    background-image: url('{{engine.adjustStaticsUrl("/static/background.jpg")}}');
}

.dicepoof {
    background-image: url('{{engine.adjustStaticsUrl("/static/dice_poof.png")}}');
}

div.rollbox > span > span.maxani {
    background-image: url('{{engine.adjustStaticsUrl("/static/dice_max.png")}}');
}

div#rollhistory {
    background-image: url('{{engine.adjustStaticsUrl("/static/dicetray.png")}}');
}
    </style>
</head>

<body>
<div class="container">
