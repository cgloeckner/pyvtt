function showAssetsBrowser() {
    loadGames(function() {
        localStorage.setItem('load_from', game)
        loadAssets()
    })
}

function onReloadAssets() {
    let game_url = $('#games').find(':selected').val()
    localStorage.setItem('load_from', game_url)
    loadAssets()
}

function loadAssets() {
    // load images used in this game
    let game_url = localStorage.getItem('load_from')
    $.ajax({
        type: 'GET',
        url: `/vtt/api/assets-list/${gm}/${game_url}`,
        dataType: 'json',
        success: function(response) {
            let target = $('#assets')
            target.empty()
            let base_url = `/asset/${gm}/${game_url}`
            if (game_url == 'null') {
                base_url = '/static/assets'
            }
            
            $.each(response['images'], function(index, fname) {
                var tmp = new Image()
                tmp.src = base_url + '/' + fname
                target.append(tmp)
                
                var node = $(target[0].lastChild)
                node.on('dragstart', function(event) {
                    onDragAsset(fname, event)
                })
                node.on('dragend', onDropAsset)
            })
            
            $('#assetsbrowser').fadeIn(100)
            
        }, error: function(response, msg) {
            if ('responseText' in response) {
                handleError(response)
            } else {
                showError('SERVER NOT FOUND')
            }
        }
    })
}

function loadGames(next) {
    // load games of this gm
    $.ajax({
        type: 'GET',
        url: `/vtt/api/games-list/${gm}`,
        dataType: 'json',
        success: function(response) {
            let target = $('#games')
            $.each(response['games'], function(index, fname) {
                var tmp = new Option(fname, fname)
                tmp.selected = (fname == game)
                target.append(tmp)
            })

            next()
            
        }, error: function(response, msg) {
            if ('responseText' in response) {
                handleError(response)
            } else {
                showError('SERVER NOT FOUND')
            }
        }
    })
}

function onDragAsset(fname, event) {
    localStorage.setItem('drag_data', fname)
}

function urlToFile(url, resolve) {
    fetch(url)
        .then(res => res.blob())
        .then(blob => {
            let file = new File([blob], 'upload.png', {type: blob.type})
            resolve(file)
        })
}

function onDropAsset(event) {    
    let x = mouse_x
    let y = mouse_y
    let drag_data = localStorage.getItem('drag_data')
    localStorage.removeItem('drag_data')
    
    let game_url = localStorage.getItem('load_from')

    if (game_url == 'null' || game_url == game) {
        let url = `/static/assets/${drag_data}`
        if (game_url == game) {
            let url = `/asset/${gm}/${game_url}/${drag_data}`
        }
        // directly create token
        writeSocket({
            'OPID' : 'CREATE',
            'posx' : x,  
            'posy' : y,
            'size' : default_token_size,
            'urls' : [url]
        })
    
    } else {
        // upload image to this game and proceed as usual
        urlToFile(url, function(file) {
            fetchMd5FromImages([file], function(md5s) {
                uploadFilesViaMd5(gm_name, game, md5s, [file], mouse_x, mouse_y);
            })
        })
    }
}

function hideAssetsBrowser() {
    $('#assetsbrowser').fadeOut(100);
}


function initUpload() {
    $('#fileupload')[0].click(); 
    $('#assetsbrowser').fadeOut(100);
}

function browseUpload() {
    // test upload data sizes
    var queue = $('#fileupload')[0];

    var error_msg = '';
    $.each(queue.files, function(index, file) {
        if (error_msg != '') {
            return;
        }

        error_msg = checkFile(file, index);
    });

    if (error_msg != '') {
        showError(error_msg);
        return;
    }
    
    // upload files
    fetchMd5FromImages(queue.files, function(md5s) {
        uploadFilesViaMd5(gm_name, game_url, md5s, queue.files, MAX_SCENE_WIDTH / 2, MAX_SCENE_WIDTH * canvas_ratio / 2);
    });
}

function browseGmUpload(url_regex, gm_url) {
    showInfo('LOADING');
    
    // test upload data sizes
    var queue = $('#fileupload')[0];
    
    var sizes_ok = true;
    if (queue.files.length != 1) {   
        showError('USE A SINGLE FILE');
        return;
    }
    var max_filesize = MAX_BACKGROUND_FILESIZE;
    var file_type    = 'BACKGROUND';
    if (queue.files[0].name.endsWith('.zip')) {
        max_filesize = MAX_GAME_FILESIZE;
        file_type    = 'GAME';
    }
    if (queue.files[0].size > max_filesize * 1024 * 1024) {
        showError('TOO LARGE ' + file_type + ' (MAX ' + max_filesize + ' MiB)');
        return;
    }
    
    // fetch upload data
    var f = new FormData($('#fileform')[0]);

    tryGameCreation(f, url_regex);
}
