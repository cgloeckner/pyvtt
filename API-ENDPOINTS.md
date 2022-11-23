# API Endpoint Documentation

The VTT offers some JSON-based API endpoints.

## `/vtt/api/users`

- number of `total` and `abandoned` (soon expire) `gms`
- number of `total` and `running` `games`

## `/vtt/api/cleanup`

- `server time` when the next cleanup will occure
- `time left` until the next cleanup (in seconds)

## `/vtt/api/build`

- `title` of the vtt instance
- `version` of the vtt is running
- `git_hash` of the git version that is in use
- `debug_hash` used for debugging purpose

## `/vtt/api/logins`

- number of users for all `locations` (based on IP)
- number of users for all `platforms` (based on browser agent)
- number of users for all `browsers` (based on browser agent)

## `/vtt/api/auth0`

- number of users that use a specific identify provider to login

## `/vtt/api/games-list/<gmurl>`

- `gameurl` for each of the gm's `games`

## `/vtt/api/assets-list/<gmurl>/<gameurl>`

- list of `images` and `audio` file names for the specified game
