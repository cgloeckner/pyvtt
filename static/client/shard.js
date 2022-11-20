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
            console.log(response)
            if (response.flag != null) {
                $(`#flag${index}`)[0].innerHTML = response.flag
            }

            if (response.title != null) {
                let target = $(`#title${index}`)
                let title = response.title

                if (response.build.version != null) {
                    title += ` v${response.build.version}`

                    let build_hash = `git sha ${response.build.git_hash}`
                    if (response.build.debug_hash) {
                        build_hash += ' (debug)'
                    }  
                    target[0].title = build_hash
                }

                target[0].innerHTML = title
            }

            if (response.games != null) {
                $(`#games${index}`)[0].innerHTML = response.games
            }
        }
    })
}
