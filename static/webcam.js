/// Settings for webcam usage
const constraints = {
    audio: false,
    video: {
        width: 1600, height: 900
    }
};

function initWebcam() {
    navigator.mediaDevices.getUserMedia(constraints)
    .then(function(stream) { onWebcamReady(stream); })
    .catch(function(err) {
        showError('CANNOT ACCESS WEBCAM');
    });
}

function onWebcamReady(stream) {
    window.stream = stream;
    $('#video')[0].srcObject = stream;
    $('#camerapreview').fadeIn(500);
    
    $('#applySnapshot').hide();
}

function onTakeSnapshot() {
    var preview = $('#snapshot')[0]
    var context = preview.getContext('2d');
    context.clearRect(0, 0, preview.width, preview.height);
    context.drawImage($('#video')[0], 0, 0, preview.width, preview.height);
    
    $('#applySnapshot').fadeIn(100);
}

function onApplyBackground() {
    showInfo('LOADING');
    
    // fetch JPEG-data from canvas
    var preview = $('#snapshot')[0]
    var url = preview.toDataURL("image/jpg");

    // prepare upload form data
    var blob = getBlobFromDataURL(url);
    var f = new FormData();
    f.append('file[]', blob, 'snapshot.jpg');

    uploadBackground(gm_name, game_url, f);
}

function closeWebcam() {
    $('#camerapreview').fadeOut(500);
    
    $('#video')[0] = null;
    window.stream  = null;    
    var preview = $('#snapshot')[0];
    var context = preview.getContext('2d');
    context.clearRect(0, 0, preview.width, preview.height);
}
