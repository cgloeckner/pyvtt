/**
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
*/

function queryShard(index, host) {
    $.ajax({
        url: '/vtt/query/' + index,
        type: 'GET',
        success: function(response) {
            if (response.flag != null) {
                $(`#flag${index}`)[0].innerHTML = response.flag
            }
            if (response.title != null) {
                $(`#title${index}`)[0].innerHTML = response.title
            }
            if (response.games != null) {
                $(`#games${index}`)[0].innerHTML = response.games
            }
        }
    })
}
