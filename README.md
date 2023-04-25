# PerplexAmped

PerplexAmped is a Discord Rich Presence implementation for Plex music.

<p align="center">
    <img src="https://i.imgur.com/cC7CiuC.png" draggable="false">
</p>

## Features

-   Modern and beautiful Rich Presence for music.
-   Uses the album covers from your library
-   Lightweight console application that runs in the background.
-   Support for two-factor authentication (2FA) at login.
-   Prioritize multiple Plex media servers and users with one configuration.

## Setup

PerplexAmped is built for [Python 3.11](https://www.python.org/) or greater.

Note: A Discord desktop client must be connected on the same device that PerplexAmped is running on.

1. Install required dependencies using [Poetry](https://python-poetry.org/): `poetry install`
2. Rename `config_example.json` to `config.json`, then provide the configurable values.
3. Start PerplexAmped: `python perplex.py`

**Configurable Values:**

-   `options`
    - `thumbnailSize`: Size of downloaded image (ex. 128px)
    - `refreshRate`: How often session state is checked
-   `logging`
    - `severity`: Minimum [Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html) severity level to display in the console (do not modify unless necessary).
-   `plex`
    -   `username`: Plex username for login.
    -   `password`: Plex password for login.
    -   `twoFactor`: `true` or `false` toggle for two-factor authentication prompt at login.
    -   `servers`: List of Plex media servers, in order of priority.
    -   `users`: List of Plex users, in order of priority.
-   `discord`
    -   `appId`: Discord application ID (do not modify unless necessary).
-   `imgur`
    -   `clientId`: Imgur API upload ID (do not modify unless necessary).
