import asyncio
import logging
import os
import pathlib
import sys
from os.path import join, dirname
from dotenv import load_dotenv

import aiohttp
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bleepingcomrss import bleepingcom
from discord import Embed, HTTPException, Webhook
from hackernews import hackernews
from otxalien import otxalien

#################### LOG CONFIG #########################

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

log = logging.getLogger("cybersecstories")
log.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S"
)

# Log to file
filehandler = logging.FileHandler("cybersec_stories.log", "a", "utf-8")
filehandler.setLevel(logging.DEBUG)
filehandler.setFormatter(formatter)
log.addHandler(filehandler)

# Log to stdout too
streamhandler = logging.StreamHandler()
streamhandler.setLevel(logging.INFO)
streamhandler.setFormatter(formatter)
log.addHandler(streamhandler)

#################### LOADING #########################


def load_keywords():
    # Load keywords from config file
    KEYWORDS_CONFIG_PATH = join(
        pathlib.Path(__file__).parent.absolute(), "config/config.yaml"
    )
    try:

        with open(KEYWORDS_CONFIG_PATH, "r") as yaml_file:
            keywords_config = yaml.safe_load(yaml_file)
            print(f"Loaded keywords: {keywords_config}")
            ALL_VALID = keywords_config["ALL_VALID"]
            DESCRIPTION_KEYWORDS_I = keywords_config["DESCRIPTION_KEYWORDS_I"]
            DESCRIPTION_KEYWORDS = keywords_config["DESCRIPTION_KEYWORDS"]
            PRODUCT_KEYWORDS_I = keywords_config["PRODUCT_KEYWORDS_I"]
            PRODUCT_KEYWORDS = keywords_config["PRODUCT_KEYWORDS"]

            return (
                ALL_VALID,
                DESCRIPTION_KEYWORDS,
                DESCRIPTION_KEYWORDS_I,
                PRODUCT_KEYWORDS,
                PRODUCT_KEYWORDS_I,
            )
    except Exception as e:
        log.error(f"Loading keyword Error:{e}")
        sys.exit(1)


#################### SEND MESSAGES #########################


async def send_discord_message(message: Embed):
    """Send a message to the discord channel webhook"""

    discord_webhok_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not discord_webhok_url:
        print("DISCORD_WEBHOOK_URL wasn't configured in the secrets!")
        return

    await sendtowebhook(webhookurl=discord_webhok_url, content=message)


async def sendtowebhook(webhookurl: str, content: Embed):
    async with aiohttp.ClientSession() as session:
        try:
            webhook = Webhook.from_url(webhookurl, session=session)
            await webhook.send(embed=content)

        except HTTPException as e:
            log.error(f"HTTP Error: {e}")
            os.system("kill 1")
        except Exception as e:
            log.debug(f"{e}")
            os.system("kill 1")


#################### MAIN BODY #########################
async def itscheckintime():

    try:

        (
            ALL_VALID,
            DESCRIPTION_KEYWORDS,
            DESCRIPTION_KEYWORDS_I,
            PRODUCT_KEYWORDS,
            PRODUCT_KEYWORDS_I,
        ) = load_keywords()

        # bleeping
        bc = bleepingcom(
            ALL_VALID,
            DESCRIPTION_KEYWORDS,
            DESCRIPTION_KEYWORDS_I,
            PRODUCT_KEYWORDS,
            PRODUCT_KEYWORDS_I,
        )
        bc.load_lasttimes()
        bc.get_new_stories()

        if bc.new_stories:  # if bc has entries
            for story in bc.new_stories:
                story_msg = bc.generate_new_story_message(story)
                await send_discord_message(story_msg)

        bc.update_lasttimes()

        # otxalien
        alien = otxalien(
            ALL_VALID,
            DESCRIPTION_KEYWORDS,
            DESCRIPTION_KEYWORDS_I,
            PRODUCT_KEYWORDS,
            PRODUCT_KEYWORDS_I,
        )
        alien.load_lasttimes()
        alien.get_new_pulse()

        if alien.new_pulses:
            for pulse in alien.new_pulses:
                pulse_msg = alien.generate_new_pulse_message(
                    pulse
                )  # return an embed pulse only if there is a description in subscribed pulse
                if pulse_msg:
                    await send_discord_message(pulse_msg)

        alien.get_modified_pulse()

        if alien.mod_pulses:
            for mod_pulse in alien.mod_pulses:
                mod_pulse_msg = alien.generate_mod_pulse_message(mod_pulse)
                await send_discord_message(mod_pulse_msg)

        alien.update_lasttimes()

        hn = hackernews(
            ALL_VALID,
            DESCRIPTION_KEYWORDS,
            DESCRIPTION_KEYWORDS_I,
            PRODUCT_KEYWORDS,
            PRODUCT_KEYWORDS_I,
        )
        hn.load_lasttimes()
        hn.get_new_stories()

        if hn.new_news:
            for hnews in hn.new_news:
                news_msg = hn.generate_new_story_message(hnews)
                await send_discord_message(news_msg)

        hn.update_lasttimes()

    except Exception as e:
        log.error(f"{e}")


if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(itscheckintime, "interval", minutes=5)
    scheduler.start()
    print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

    # Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        log.error(f"{e}")
        raise e
