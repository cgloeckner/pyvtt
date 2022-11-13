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

/// TODO: load blob from url to build file :)
function urlToFile(url, resolve) {
    fetch(url)
        .then(res => res.blob())
        .then(blob => {
            let file = new File([blob], 'upload.png', {type: blob.type})
            resolve(file)
        })
}

function onDropAsset(event) {
    let game_url = localStorage.getItem('load_from')
    
    let x = mouse_x
    let y = mouse_y
    let url = `/asset/${gm}/${game_url}`
    
    url += '/' + localStorage.getItem('drag_data')
    localStorage.removeItem('drag_data')

    if (game_url == game) {
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
