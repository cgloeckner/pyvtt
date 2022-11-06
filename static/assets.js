function showAssetsBrowser() {
    // ajax load browser
    let url = window.location.pathname.replace('game', 'vtt/api/assets-list')
    
    $.ajax({
        type: 'GET',
        url: url,
        dataType: 'json',
        success: function(response) {
            let target = $('#assets');
            target.empty()
            let base_url = window.location.pathname.replace('game', 'asset')
            
            $.each(response['images'], function(index, fname) {
                var tmp = new Image();
                tmp.src = base_url + '/' + fname;
                target.append(tmp)
                
                var node = $(target[0].lastChild)
                node.on('dragstart', function(event) {
                    onDragAsset(fname, event)
                })
                node.on('dragend', onDropAsset)
            });
            
            $('#assetsbrowser').fadeIn(100)
            
        }, error: function(response, msg) {
            if ('responseText' in response) {
                handleError(response);
            } else {
                showError('SERVER NOT FOUND');
            }
        }
    });
}

function onDragAsset(fname, event) {
    localStorage.setItem('drag_data', fname)
}

function onDropAsset(event) {
    let x = mouse_x
    let y = mouse_y
    let url = window.location.pathname.replace('game', 'asset')
    if (url == null) {
        return
    }
    url += '/' + localStorage.getItem('drag_data')

    writeSocket({
        'OPID' : 'CREATE',
        'posx' : x,  
        'posy' : y,
        'size' : default_token_size,
        'urls' : [url]
    })

    localStorage.removeItem('drag_data')
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
