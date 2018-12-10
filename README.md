# Restful Webservice to allow the users to player a bowling game [![Build Status](https://travis-ci.org/krishnanand/bowling_game.svg?branch=master)](https://travis-ci.org/krishnanand/bowling_game)

## Table of Contents

- [Requirements](#requirements)
- [Setup](#setup)
- [API Endpoints](#api-endpoints)
  * [Register Game](#registergame)
      1. [Registration Success Response](#register-success-response)
      2. [Registration Error Response](#register-error-response)
  * [Play the game](#play-game)
      1. [Scoring Format](#scoring-format)
      2. [Success Responses](#success-responses)
         * [Open Frame - Success Response](#open-frame-success-response)
         * [Strike - Success Response](#strike-spare-success-response)
         * [Spare - Success Response](#strike-spare-success-response)
      3. [Error](#error-responses)
         * [Game Not Found](#game-not-found-error)
         * [Invalid Scoring Format](#score-format-invalid-error)
         * [Game Not Found](#game-already-played-error)
         * [Two threads attempting to score at the same time](#optimistic-locking-error)
  * [Get Frame Score](#get-frame-score)
      1. [Success Response](#score-success-response)
      2. [Error](#score-error-response)
         * [Game Not Found](#score-game-not-found)


### Requirements ###

* Python 3.6.5
* Django framework
* Django Rest Framework

### Setup ###

* Clone the repository.

* Install Python 3.6.5 and above. You can use your favourite tool to install the software (HomeBrew, pyenv)

* Set up virtualenv with the following command ``virtualenv -p `which python3` env``

* Install the python packages required by the project by executing `pip install -r requirements.txt`.

* Run the migration scripts by executing the following commands from the home directory `cd bowling_game && python manage.py migrate`

* Run the command `python manage.py runserver` to start the server.

# API Endpoints ###

## <a name="registergame">Register Game</a>

#### POST /game/register ####

Registers a bowling game for the contestant and assigns a unique 16 character alpha numeric string representing a unique game id.

#### <a name="register-success-response">Response Body</a> ####

A response body will include:

● a status code of 201 Created

● Response Body Properties

| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| game_id  | string | Unique game id |true
| created | timestamp | UTC timestamp |true


````
{
    "game_id": "MYCjFlD8Rc9dzu5W",
    "created": "2018-07-19T22:05:41.647970Z"
}
````

#### <a name="register-error-response">Error Response Body</a> ####

A error response will be an error of error objects.

| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| errors  | array | array of errors |true |

where each error object consists of the following fields

| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| error code  | number | error code indicating the kind of error|true |
| error message  | string | user friendly message |true |

The sample response is given below:

```
{
    "errors": [
        {
          'error_code': 403,
          'error_message': 'Forbidden from registering a game.'
        }
    ]
}
```

### <a name="play-game">Play the game.</a> ###

#### POST /game/<game_id>/score/<score> ####

Registers the score of the contestant for a given frame, and returns the total score in the response payload.

Response body after playing a frame is given below:


| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| game  | string | Unique game id passed as a path variable |true|
| frame | int | number of frames played |true|
| frame_score | int | sum of score of each attempt in a frame; if attempt resulted in a spare or a strike, the value returns `null` till the time it can be calculated |true|
| total_score_for_frame | int | total game score; if the score can not be calculated at that time, then `null` is returned. This is especially in case of strikes, or spares |true|

#### <a name="scoring-format">Scoring Format</a> ####

All scores in an open frame are separated by `-`. For example, a score of `7-2` indicates that the player knocked down 7 pins in the first attempt, and 2 pins in the second attempt.

| Score | Description |
| :---         |     :---      |
| X-X-X  | All strikes in all 3 attempts in the last frame|
| X-X-<0-9> | two strikes and open frame in the last frame|
| X-<0-9>/ | strike and a spare in the last frame)
| X-<0-9>-<0-9> | strike and two open scores in the last frame|
| X | strike in any frame other than the last frame |
| <0-9>/X | spare and a strike in the last frame |
| <0-9>/<0-9> | spare and an open frame in the last frame|
| <0-9>/ | spare for any attempt except in the last frame|
| <0-9>-<0-9> | score for a open frame |

#### <a name="success-responses">Success Response</a> ####

#### <a name="open-frame-success-response">1. Open Frame: Success Response</a> ####

The sample response below gives the score after an open frame.

```
{
    "game": "MYCjFlD8Rc9dzu5W",
    "frame": 6,
    "frame_score": 9,
    "total_score_for_frame": 105
}
```

#### <a name="strike-spare-success-response">2. Strike/Spare Success Response</a> ####

The sample response below gives the score after a strike or a spare.

```
{
    "game": "MYCjFlD8Rc9dzu5W",
    "frame": 6,
    "frame_score": null,
    "total_score_for_frame": 105/<null> (score that has been calculated so far, or `null` if it can not be calculated until now)
}
```

#### <a name="error-responses">Error Responses</a> ####

The error response is body is an array of errors.

| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| errors  | array | array of error objects |true |

where each error object consists of the following fields

| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| error code  | number | error code indicating the kind of error|true |
| error message  | string | user friendly message |true |

Some of the sample responses are given below

#### <a name="game-not-found-error">1. Game Not Found</a> ####

This will return a 404 error if no record for the game was found in the database.

```
{
    "errors": [
        {
          "error_code": 404,
          "error_message" : "No game was found for the game id: <game_id>."
        }
    ]
}
```

#### <a name="score-format-invalid-error">2. Invalid Scoring Format</a> ####

This will return a 404 error if no record for the game was found in the database.

```
{
    "errors": [
        {
          "error_code": 400,
          "error_message" : "Score format: <score> is invalid."
        }
    ]
}
```

#### <a name="game-already-played-error">3. Game Not Found</a> ####

This will return a 404 error if no record for the game was found in the database.

```
{
    "errors": [
        {
          "error_code": 400,
          "error_message" : "Game:\'<game_id>\' has already been played."
        }
    ]
}
```

#### <a name="optimistic-locking-error">4. Two threads attempting to score at the same time.</a> ####

This will return a 404 error if no record for the game was found in the database.

```
{
    "errors": [
        {
          "error_code": 500,
          "error_message" : "Unable to save score: '<score>' for game: '<game_id>'."
        }
    ]
}
```

### <a name="get-frame-score">Get the current score.</a> ###

#### GET /game/<game_id>/score ####

Returns the score of the game at any given time.

The response body consists of

| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| game_id  | string | Unique game id passed as a path variable |true|
| total_score | int | Total score till the present time|true|

#### <a name="score-success-response">1. Success Response</a>

The sample response is given below.
```
{
    "total_score": 182,
    "game_id": "<game_id>"
}
```

#### <a name="score-success-response">2. Error Response</a> ####
The error response is body is an array of errors.

| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| errors  | array | array of error objects |true |

where each error object consists of the following fields

| Name | Type | Description | Read only |
| :---         |     :---:      |          :--- |      :---:      |
| error code  | number | error code indicating the kind of error|true |
| error message  | string | user friendly message |true |

Some of the sample responses are given below

#### <a name="score-game-not-found">Game Not Found</a> ####

```
{
    "errors": [
        {
            "error_code": 404,
            "error_message": "No game was found for the game id: <game_id>."
        }
    ]
}
```
