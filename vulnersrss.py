import datetime
import json
import logging
import pathlib
from os.path import join
from bs4 import BeautifulSoup


import feedparser
import pytz

gmt = pytz.timezone('GMT')


class vulners:
    def __init__(self, valid, keywords, keywords_i, product, product_i):
        self.valid = valid
        self.keywords = keywords
        self.keywords_i = keywords_i
        self.product = product
        self.product_i = product_i

        self.VULNERS_UR = "https://vulners.com/rss.xml"
        self.PUBLISH_VULNERS_JSON_PATH = join(
            pathlib.Path(__file__).parent.absolute(
            ), "output/vulners_record.json"
        )
        self.VULNERS_TIME_FORMAT = "%a, %d %b %Y %H:%M:%S %Z"
        self.LAST_PUBLISHED = datetime.datetime.now(
            gmt) - datetime.timedelta(days=1)
        self.logger = logging.getLogger(__name__)

        self.new_stories = []
        self.vulners_title = []

    ################## LOAD CONFIGURATIONS ####################

    def load_lasttimes(self):
        # Load lasttimes from json file

        try:
            with open(self.PUBLISH_VULNERS_JSON_PATH, "r") as json_file:
                published_time = json.load(json_file)
                self.LAST_PUBLISHED = datetime.datetime.strptime(
                    published_time["LAST_PUBLISHED"], self.VULNERS_TIME_FORMAT
                )

        # If error, just keep the fault date (today - 1 day)
        except Exception as e:
            self.logger.error(f"VULNERS-ERROR-1: {e}")

    def update_lasttimes(self):

        # Save lasttimes in json file
        try:
            with open(self.PUBLISH_VULNERS_JSON_PATH, "w") as json_file:
                json.dump(
                    {
                        "LAST_PUBLISHED": self.LAST_PUBLISHED.replace(
                            tzinfo=gmt).strftime(self.VULNERS_TIME_FORMAT)
                    },
                    json_file,
                )
        except Exception as e:
            self.logger.error(f"VULNERS-ERROR-2: {e}")

    ################## SEARCH STORIES FROM VULNERS ####################

    def get_stories(self, link):
        newsfeed = feedparser.parse(link)
        return newsfeed

    def filter_stories(self, stories, last_published: datetime.datetime):
        filtered_stories = []
        new_last_time = last_published
        for story in stories:
            story_time = datetime.datetime.strptime(
                story["published"], self.VULNERS_TIME_FORMAT
            )
            if story_time > last_published:
                if self.valid or self.is_summ_keyword_present(story["description"]):

                    filtered_stories.append(story)

            if story_time > new_last_time:
                new_last_time = story_time

        return filtered_stories, new_last_time

    def is_summ_keyword_present(self, summary: str):
        # Given the summary check if any keyword is present
        return any(w in summary for w in self.keywords) or any(
            w.lower() in summary.lower() for w in self.keywords_i
        )  # for each of the word in description keyword config, check if it exists in summary.

    def get_new_stories(self):
        stories = self.get_stories(self.VULNERS_UR)
        self.new_stories, self.LAST_PUBLISHED = self.filter_stories(
            stories["entries"], self.LAST_PUBLISHED
        )
        self.remove_html_from_stories()

        self.vulners_title = [new_story["title"]
                              for new_story in self.new_stories]
        print(f"Vulners Stories: {self.vulners_title}")
        self.logger.info(f"Vulners Stories: {self.vulners_title}")

    def remove_html_from_stories(self):
        for story in self.new_stories:
            story['description'] = BeautifulSoup(
                story['description'], "lxml").get_text()