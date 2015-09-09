
# Hip-Trebek

A Jeopardy! bot for Hipchat, powered by the [jService](http://jservice.io/) API. Sets up a perpetual game of Jeorpardy! in your HipChat channels.

![](http://i.imgur.com/bzQwqzO.png)

## Requirements

* You'll need a [HipChat](https://hipchat.com) account, obviously, 
* A free [Heroku](https://www.heroku.com/) account to host the bot. 
* You'll also need to be able to set up new integrations in HipChat; if you're not able to do this, contact someone with admin access in your organization. With v2 of the HipChat API, you should be able to create an API Token under your account profile.
* A Free [Redis Cloud](https://redislabs.com/) account

## Installation

1. Set up a HipChat outgoing web hook at https://www.hipchat.com/docs/apiv2/method/create_webhook. Make sure to pick a trigger word, such as `/trebek`. 

2. Click this button to set up your Heroku app: [![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)   
If you'd rather do it manually, then just clone this repo, set up a Heroku app with Redis Cloud (the free level is more than enough for this), and deploy hip-trebek there. Make sure to set up the config variables in
[.env.example](https://github.com/yanigisawa/hip-trebek/blob/master/.env.example) in your Heroku app's settings screen.

## Usage

* `/trebek jeopardy`: starts a round of Jeopardy! hip-trebek will pick a category and score for you.
* `/trebek what/who is/are [answer]`: sends an answer. Remember, responses must be in the form of a question!
* `/trebek score`: shows your current score.
* `/trebek leaderboard`: shows the current top scores.
* `/trebek loserboard`: shows the current bottom scores.
* `/trebek answer`: displays the answer to the previous question without starting a new round
* `/trebek invalid`: submits the active question as invalid to [jservice.](http://jservice.io/) Use this if the clue requires visual or audio clues not available in chat.
* `/trebek help`: shows this help information.

## Credits & acknowledgements

Big thanks to [Steve Ottenad](https://github.com/sottenad) for building [jService](http://jservice.io/), the service that powers this bot.

This code is a python / HipChat port of [trebekbot](https://github.com/gesteves/trebekbot) from ruby / Slack. The structure of this bot, repo, and readme are directly descended from his work.

## Contributing

Feel free to open a new issue if you have questions, concerns, bugs, or feature requests. Just remember that I did this for fun, for free, in my free time, and I may not be able to help you, respond in a timely manner, or implement any feature requests.


The MIT License (MIT)

Copyright (c) 2015 James Alexander

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

