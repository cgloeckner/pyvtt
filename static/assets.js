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

function onDropAsset(event) {
    let game_url = localStorage.getItem('load_from')
    
    let x = mouse_x
    let y = mouse_y
    let url = `/asset/${gm}/${game_url}`
    if (url == null) {
        return
    }
    url += '/' + localStorage.getItem('drag_data')
    
    if (game_url == game) {
        // directly create token
        writeSocket({
            'OPID' : 'CREATE',
            'posx' : x,  
            'posy' : y,
            'size' : default_token_size,
            'urls' : [url]
        })

        localStorage.removeItem('drag_data')
    
    } else {
        // TODO: re-upload it to this game
        // TODO: create token with url local to this game
    }

    
}

function hideAssetsBrowser() {
    $('#assetsbrowser').fadeOut(100);
}

/*
function mobileUpload() {
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
*/
