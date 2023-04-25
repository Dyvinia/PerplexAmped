import json
import urllib.parse
import pyimgur
import os
from datetime import datetime
from pathlib import Path
from sys import exit, stderr
from time import sleep
from typing import Any, Dict, List, Optional, Self

import httpx
from loguru import logger
from plexapi.audio import TrackSession
from plexapi.media import Media
from plexapi.myplex import MyPlexAccount, MyPlexResource, PlexServer
from pypresence import Presence

class PerplexAmped:
    """
    Discord Rich Presence implementation for Plex music.

    https://github.com/Dyvinia/PerplexAmped
    Forked from https://github.com/EthanC/Perplex 
    """

    def Initialize(self: Self) -> None:
        """Initialize PerplexAmped and begin primary functionality."""

        logger.info("PerplexAmped")
        logger.info("https://github.com/Dyvinia/PerplexAmped")

        self.config: Dict[str, Any] = PerplexAmped.LoadConfig(self)

        PerplexAmped.SetupLogging(self)

        plex: MyPlexAccount = PerplexAmped.LoginPlex(self)
        discord: Presence = PerplexAmped.LoginDiscord(self)

        prevSession: Optional[TrackSession] = None
        prevState = ""

        while True:
            session: Optional[TrackSession] = PerplexAmped.FetchSession(self, plex)

            if session:
                if session != prevSession or session.player.state != prevState:
                    if type(session) is TrackSession:
                        status: Dict[str, Any] = PerplexAmped.BuildTrackPresence(self, session)

                    success: bool = PerplexAmped.SetPresence(self, discord, status)

                    # Reestablish a failed Discord Rich Presence connection
                    if not success:
                        discord = PerplexAmped.LoginDiscord(self)
            else:
                try:
                    discord.clear()
                except Exception:
                    pass
                sleep(15.0)

            if session is None:
                prevSession = None
                prevState = ""

            # wait before refresh
            sleep(self.config["plex"]["refreshRate"])

    def LoadConfig(self: Self) -> Dict[str, Any]:
        """Load the configuration values specified in config.json"""

        try:
            with open("config.json", "r") as file:
                config: Dict[str, Any] = json.loads(file.read())
        except Exception as e:
            logger.critical(f"Failed to load configuration, {e}")

            exit(1)

        logger.success("Loaded configuration")

        return config

    def SetupLogging(self: Self) -> None:
        """Setup the logger using the configured values."""

        settings: Dict[str, Any] = self.config["logging"]

        if (level := settings["severity"].upper()) != "DEBUG":
            try:
                logger.remove()
                logger.add(stderr, level=level)

                logger.success(f"Set logger severity to {level}")
            except Exception as e:
                # Fallback to default logger settings
                logger.add(stderr, level="DEBUG")

                logger.error(f"Failed to set logger severity to {level}, {e}")

    def LoginPlex(self: Self) -> MyPlexAccount:
        """Authenticate with Plex using the configured credentials."""

        settings: Dict[str, Any] = self.config["plex"]

        account: Optional[MyPlexAccount] = None

        if Path("auth.txt").is_file():
            try:
                with open("auth.txt", "r") as file:
                    auth: str = file.read()

                account = MyPlexAccount(token=auth)
            except Exception as e:
                logger.error(f"Failed to authenticate with Plex using token, {e}")

        if not account:
            username: str = settings["username"]
            password: str = settings["password"]

            if settings["twoFactor"]:
                print(f"Enter Verification Code: ", end="")
                code: str = input()

                if (code == "") or (code.isspace()):
                    logger.warning(
                        "Two-Factor Authentication is enabled but code was not supplied"
                    )
                else:
                    password = f"{password}{code}"

            try:
                account = MyPlexAccount(username, password)
            except Exception as e:
                logger.critical(f"Failed to authenticate with Plex, {e}")

                exit(1)

        logger.success("Authenticated with Plex")

        try:
            with open("auth.txt", "w+") as file:
                file.write(account.authenticationToken)
        except Exception as e:
            logger.error(
                f"Failed to save Plex authentication token for future logins, {e}"
            )

        return account

    def LoginDiscord(self: Self) -> Presence:
        """Authenticate with Discord using the configured credentials."""

        client: Optional[Presence] = None

        while not client:
            try:
                client = Presence(self.config["discord"]["appId"])
                client.connect()
            except Exception as e:
                logger.error(f"Failed to connect to Discord ({e}) retry in 15s...")

                sleep(15.0)

        logger.success("Authenticated with Discord")

        return client

    def FetchSession(
        self: Self, client: MyPlexAccount
    ) -> Optional[TrackSession]:
        """
        Connect to the configured Plex Media Server and return the active
        media session.
        """

        settings: Dict[str, Any] = self.config["plex"]

        resource: Optional[MyPlexResource] = None

        for entry in settings["servers"]:
            for result in client.resources():
                if entry.lower() == result.name.lower():
                    resource = result

                    break

            if resource:
                break

        if not resource:
            logger.critical("Failed to locate configured Plex Media Server")

            exit(1)

        try:
            global server
            if server is None:
                logger.info(f"Connecting to {resource.name}...")
                server = resource.connect()
                logger.success(f"Connected to {resource.name}")
        except Exception as e:
            logger.critical(
                f"Failed to connect to configured Plex Media Server ({resource.name}), {e}"
            )

            exit(1)

        sessions: List[Media] = server.sessions()
        active: Optional[TrackSession] = None

        if len(sessions) > 0:
            i: int = 0

            for entry in settings["users"]:
                for result in sessions:
                    if type(result) is TrackSession and entry.lower() in [alias.lower() for alias in result.usernames]:
                        active = sessions[i]

                        break

                    i += 1

        if not active:
            logger.info("No active media sessions found for configured users")
            return
        
        return active

    def BuildTrackPresence(self: Self, active: TrackSession) -> Dict[str, Any]:
        """Build a Discord Rich Presence status for the active music session."""

        result: Dict[str, Any] = {}   

        baseUrl = active.thumbUrl.split('/')[2]
        quoteUrl = urllib.parse.quote(active.parentThumb)
        plexToken = "&" + active.thumbUrl.split('?')[-1]
        url = "https://" + baseUrl + "/photo/:/transcode?width=128&height=128&minSize=1&upscale=1&url=" + quoteUrl + plexToken

        parentThumb = active.parentThumb.replace('/', '\\')

        global currentThumbPath
        global currentThumbURL
        global currentKey

        thumbFile = os.path.dirname(os.path.realpath(__file__)) + "\\cache" + parentThumb + ".png"
        linkFile = os.path.dirname(os.path.realpath(__file__)) + "\\cache" + parentThumb + ".txt"
        os.makedirs(os.path.dirname(thumbFile), exist_ok=True)

        if currentThumbPath != parentThumb:
            if not os.path.isfile(thumbFile):
                response = httpx.get(url)
                open(thumbFile, 'wb').write(response.content)
            
            if not os.path.isfile(linkFile):
                uploaded_image = pyimgur.Imgur(self.config["imgur"]["clientId"]).upload_image(thumbFile)
                currentThumbURL = uploaded_image.link
                open(linkFile, 'wt').write(currentThumbURL)
            else:
                currentThumbURL = open(linkFile, 'rt').read()
            
        
        currentThumbPath = parentThumb
        currentKey = active.key

        result["primary"] = active.titleSort
        result["secondary"] = f"by {active.originalTitle if active.originalTitle != None else active.artist().title}"
        result["remaining"] = int(active.viewOffset / 1000)
        result["imageText"] = active.parentTitle
        result["image"] = currentThumbURL
        result["state"] = active.player.state

        logger.trace(result)

        return result

    def SetPresence(self: Self, client: Presence, data: Dict[str, Any]) -> bool:
        """Set the Rich Presence status for the provided Discord client."""

        title: str = data["primary"]
        stateCaps = data["state"].capitalize()

        try:
            if data["state"] == "playing":
                client.update(
                    details=title,
                    state=data.get("secondary"),
                    start=int(datetime.now().timestamp() - data["remaining"]),
                    large_image=data["image"],
                    large_text=data["imageText"],
                    small_image="playing",
                    small_text=stateCaps,
                )

            else:
                client.update(
                    details=title,
                    state=data.get("secondary"),
                    large_image=data["image"],
                    large_text=data["imageText"],
                    small_image="paused",
                    small_text=stateCaps,
                )
        except Exception as e:
            logger.error(f"Failed to set Discord Rich Presence to {title}, {e}")

            return False

        
        logger.success(f"Set Discord Rich Presence to: {title} ({stateCaps})")

        return True


if __name__ == "__main__":
    global currentThumbPath
    currentThumbPath = ""

    global currentThumbURL
    currentThumbURL = ""

    global server
    server: Optional[PlexServer] = None
    try:
        PerplexAmped.Initialize(PerplexAmped)
    except KeyboardInterrupt:
        exit()
