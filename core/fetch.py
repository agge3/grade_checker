from tools import util

from core.shell import Shell

import os
import fnmatch
import re
import platform
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime


class Fetcher:
    def __init__(self, milestone, config, path='', date=datetime(2025, 1, 1)):
        self._shell = Shell()
        self._config = config

        self._dotenv = ".env"
        load_dotenv(self._dotenv)

        self._milestone = milestone
        print(f"Fetcher:\tmilestone:\t{self._milestone}")

        # Milestone with Professor's name appended.
        self._pmilestone = self._milestone + f"-{self._config['prof']}"
        print(f"Fetcher:\tprofessor milestone:\t{self._pmilestone}")

        # Format "milestoneX" as "milestone-X".
        self._fmilestone = util.fmt_milestone(milestone)
        print(f"Fetcher:\tformatted milestone:\t{self._fmilestone}")

        self._init_timestamp(date)
        self._init_req()
        self._init_path(path)

        self._clone = self._config['clone']

    def _init_timestamp(self, date):
        # datetime(year, month, day)
        # xxx push into json config
        self._mindate = date
        self._push_mindate = datetime(2025, 2, 27)

    def _init_req(self):
        self._auth = (os.getenv('USERNAME'), os.getenv('PAT'))
        self._headers = {
            'Authorization': f'Bearer {self._auth[1]}',
            'Accept': 'application/vnd.github.v3+json'
        }

        self._org = self._config['org']
        self._url = f"https://api.github.com/orgs/{self._org}/repos"

        glob = self._config['glob']
        self._glob = f"{self._fmilestone}-{glob}-*"

    def _init_path(self, path):
        if path != '':
            self._path = path
        else:
            self._path = f'repos/{self._pmilestone}' 

    def fetch(self):
        if self._config['fetch']['clear']:
            stdout, stderr, code = self._shell.cmd(
                    f"rm -rf {self._path} && " +
                    f"mkdir {self._path}"
            )

        # Don't paginate (GitHub(R)'s API paginates by default).
        page = 1
        while True:
            response = requests.get(self._url, headers=self._headers,
                                    params={'page' : page})
            if response.status_code != 200:
                break

            repos = response.json()
            if not repos:
                break

            for repo in repos:
                # Skip repos that are older than our specified minimum 
                # year/month.
                created_at = datetime.strptime(repo['created_at'],
                                               "%Y-%m-%dT%H:%M:%SZ")
                #print(f'Fetcher:\tfetch:\tcreated_at:\t{created_at}')
                pushed_at = datetime.strptime(repo['pushed_at'],
                                              "%Y-%m-%dT%H:%M:%SZ")
                #print(f'Fetcher:\tfetch:\tpushed_at before:\t{pushed_at}')

                if (created_at.year < self._mindate.year and
                    created_at.month < self._mindate.month):
                    continue

                if (pushed_at < self._push_mindate):
                    continue
                
                print(f'Fetcher:\tfetch:\tpushed_at after:\t{pushed_at}')

                if fnmatch.fnmatch(repo['name'], self._glob):
                    if self._clone:
                        # xxx log
                        print(
                            f'Fetcher:\tAttempting to clone {repo['name']}'
                        )

                        stdout, stderr, code = self._shell.cmd(
                            f"cd {self._path} && " +
                            f"git clone git@github.com:" +
                            f"{self._org}/{repo['name']}.git && " +
                            f"cd -"
                        )
                        print(f'Fetcher:\tfetch:\tgit clone stdout:\t{stdout}')

                        # xxx log
                        if code == 0:
                            # Push an extra newline to split entries.
                            print(
                                f"Fetcher:\tSuccessfully cloned {repo['name']}"
                            )
                        else:
                            # Push an extra newline to split entries.
                            print(f"Fetcher:\tFailed to clone\t{repo['name']}")

                    else:
                        # xxx log
                        print(f'Fetcher:\tfetch:\t{repo['name']}')

            if 'Link' not in response.headers:
                break

            page += 1
