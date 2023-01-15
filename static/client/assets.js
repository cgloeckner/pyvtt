/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
*/

function showAssetsBrowser() {
    loadGames(gm, function() {
        loadAssets()
    })
}

function loadAssets() {
    // load images used in this game
    let game_url = $('#games').find(':selected').val()
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
                tmp.id  = `asset${index}`
                tmp.src = base_url + '/' + fname
                target.append(tmp)
                
                var node = $(target[0].lastChild)
                
                node.on('dragstart', function(event) {
                    onDragAsset(fname, event)
                })
                node.on('touchstart', function(event) {
                    onDragAsset(fname, event)
                })
                
                node.on('dragend', onDropAsset)
                node.on('touchend', onDropAsset)
                
                node.on('dblclick', onQuickDropAsset)
                node.on('contextmenu', function(event) {
                    onDownloadAsset(tmp.id, fname, event)
                })
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

function loadGames(gm, next) {
    // load games of this gm
    $.ajax({
        type: 'GET',
        url: `/vtt/api/games-list/${gm}`,
        dataType: 'json',
        success: function(response) {
            let target = $('#games')
            $.each(response['games'], function(index, fname) {
                let o = $(`#games option[value="${fname}"]`)[0]
                if (o == null) {
                    var tmp = new Option(`Game: ${fname}`, fname)
                    tmp.selected = (fname == game)
                    target.append(tmp)
                }
            })
            $('#games option').first().prop('selected', true)

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

function onDropAsset(event, pos=null) {
    if (pos == null) {
        pos = [mouse_x, mouse_y]
    }
    let drag_data = localStorage.getItem('drag_data')
    localStorage.removeItem('drag_data')

    let game_url = $('#games').find(':selected').val()

    if (game_url == 'null' || game_url == game) {
        let url = `/static/assets/${drag_data}`
        if (game_url == game) {
            url = `/asset/${gm}/${game_url}/${drag_data}`
        }
        // directly create token
        writeSocket({
            'OPID' : 'CREATE',
            'posx' : pos[0],
            'posy' : pos[1],
            'size' : default_token_size,
            'urls' : [url]
        })
    
    } else {
        let url = `/asset/${gm}/${game_url}/${drag_data}`
        // upload image to this game and proceed as usual
        urlToFile(url, function(file) {
            fetchMd5FromImages([file], function(md5s) {
                uploadFilesViaMd5(gm_name, game, md5s, [file], pos[0], pos[1])
            })
        })
    }
}

function onQuickDropAsset(event) {
    localStorage.setItem('drag_data', fname)
    let center = [viewport['x'], viewport['y']]
    onDropAsset(event, center)
}

function onDownloadAsset(id, fname, event) {
    let asset = $(`#${id}`)
    fetch(asset[0].src).then((image) => {
        image.blob().then((blob) => {
            let link  = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = fname
            link.click()
        })
    })
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
