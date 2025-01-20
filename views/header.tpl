<!--
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
//-->

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <link rel="shortcut icon" href="/static/favicon.ico?v={{engine.version}}" type="image/x-icon">
%version = engine.get_build_sha()
%for js in ['jquery-3.3.1.min', 'md5', 'version', 'constants', 'errors', 'dropdown', 'render', 'ui', 'socket', 'gm', 'music', 'utils', 'webcam', 'drawing', 'assets']:
    <script src="/static/client/{{js}}.js?v={{version}}"></script>
%end
    <link rel="stylesheet" type="text/css" href="/static/client/normalize.css?v={{engine.version}}">
    <link rel="stylesheet" type="text/css" href="/static/client/layout.css?v={{engine.version}}">
    <title>{{engine.title}}: {{title}}</title>
</head>

<body>
<div class="container">
