import os
import fnmatch
import re
import platform
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

clone = False

class Fetcher:
    def __init__(self, shell, milestone):
        self._shell = shell
        self._milestone = milestone
        # Format "milestoneX" as "milestone-X".
        self._fmilestone = re.sub(r"(\D)(\d+)", r"\1-\2", milestone)
        self._dotenv = ".env"
        load_dotenv(self._dotenv)
        self._auth = (os.getenv('USERNAME'), os.getenv('PAT'))
        self._org = os.getenv('ORGANIZATION')
        self._glob = f"{self._fmilestone}*"
        self._url = f"https://api.github.com/orgs/{self._org}/repos"
        self._headers = {
            'Authorization': f'Bearer {self._auth[1]}',
            'Accept': 'application/vnd.github.v3+json'
        }

    def fetch(self):
        stdout, stderr, code = self._shell.cmd(
                f"rm -rf repos/{self._milestone} && " +
                f"mkdir repos/{self._milestone}"
        )

        # Don't paginate (GitHub(R)'s API paginates by default).
        page = 1
        while True:
            response = requests.get(self._url, headers=self._headers, params={'page' : page})
            if response.status_code != 200:
                break

            repos = response.json()
            if not repos:
                break

            for repo in repos:
                if fnmatch.fnmatch(repo['name'], self._glob):
                    if clone:
                        stdout, stderr, code = self._shell.cmd(
                            f"git clone git@github.com:" +
                            f"{self._org}/{repo['name']}.git"
                        )
                    else:
                        print(repo['name'])

            if 'Link' not in response.headers:
                break

            page += 1
