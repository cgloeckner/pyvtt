
function initUpload() {
    closeWebcam();
    $('#uploadscreen').fadeIn(500);
}

function mobileUpload() {
    notifyUploadStart();
    
    // test upload data sizes
    var queue = $('#fileupload')[0];

    var error_msg = '';
    $.each(queue.files, function(index, file) {
        if (error_msg != '') {
            notifyUploadFinish();
            return;
        }
        
        content = file.type.split('/')[0];
        
        var max_filesize = 0;
        var file_type    = '';
        // check image filesize
        if (content == 'image') {
            max_filesize = MAX_TOKEN_FILESIZE;
            file_type    = 'TOKEN';
            if (index == 0 && !background_set) {
                // first file is assumed as background image
                max_filesize = MAX_BACKGROUND_FILESIZE
                file_type = 'BACKGROUND';
            }

        // check music filesize
        } else if (content == 'audio') {
            max_filesize = MAX_MUSIC_FILESIZE;
            file_type    = 'MUSIC';
        }

        if (file.size > max_filesize * 1024 * 1024) {
            error_msg = 'TOO LARGE ' + file_type + ' (MAX ' + max_filesize + ' MiB)';
        }

        if (content == 'audio' && $('#musicslots').children().length == MAX_MUSIC_SLOTS) {
            showError('QUEUE FULL, RIGHT-CLICK SLOT TO CLEAR');
        }
    });

    if (error_msg != '') {
        notifyUploadFinish();
        showError(error_msg);
        return;
    }

    // upload files
    var f = new FormData($('#fileform')[0]);

    $.ajax({
        url: '/' + gm_name + '/' + game_url + '/upload',
        type: 'POST',
        data: f,
        contentType: false,
        cache: false,
        processData: false,
        success: function(response) {
            // reset uploadqueue
            $('#fileupload').val("");

            response = JSON.parse(response);

            // load images if necessary
            if (response['urls'].length > 0) {
                $.each(response['urls'], function(index, url) {
                    loadImage(url);
                });
                
                // trigger token creation via websocket
                writeSocket({
                    'OPID' : 'CREATE',
                    'posx' : 500,
                    'posy' : 300,
                    'size' : default_token_size,
                    'urls' : response['urls']
                });
            }

            if (response['music'].length > 0) {
                if (response['music'][0] == null) {
                    // notify full slots
                    showError('QUEUE FULL, RIGHT-CLICK SLOT TO CLEAR');
                    
                } else {
                    // broadcast music upload
                    writeSocket({
                        'OPID'   : 'MUSIC',
                        'action' : 'add',
                        'slots'  : response['music']
                    });
                }
            }
            
            notifyUploadFinish();
            closeUpload();
            
        }, error: function(response, msg) {
            notifyUploadFinish();
            handleError(response);
        }
    });
}

function closeUpload() {
    $('#uploadscreen').fadeOut(500);
}
