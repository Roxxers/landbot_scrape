# Landbot.io scraper

Script to scrape a number of landbot.io chat bot messages. This keeps intact choices, dialogue blocks, and image and youtube links.

## Installation

Installation requires Python 3.6+, pip, and venv

Also requires Firefox and the [Gecko drivers](https://github.com/mozilla/geckodriver/) for selenium to interact with Firefox.

```sh
git clone REPO_URL
cd landbot_scrape
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Running

TODO: Need to add section about url listing when finished doing that for multiple urls and not hardcoded.

To run the script, make sure you are source'd into the virtual env, then run

```sh
python3 main.py
```
