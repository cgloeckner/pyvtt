
function initUpload() {
    $('#fileupload')[0].click();
}

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

function mobileGmUpload(url_regex, gm_url) {
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
