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


from github import Github
from github import Auth

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
        date_env = os.getenv('FETCH_DATE')
        self._mindate = date
        if not date_env:
            self._push_mindate = date
        else:
            self._push_mindate = datetime.strptime(date_env, '%Y-%m-%d')

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

    def _load_usernames(self):
        """Load usernames from file specified in config."""
        usernames_file = self._config.get('usernames_file')
        if not usernames_file:
            print("Fetcher:\tNo usernames_file specified in config")
            return []
        
        try:
            with open(usernames_file, 'r') as f:
                usernames = [line.strip() for line in f if line.strip()]
            print(f"Fetcher:\tLoaded {len(usernames)} usernames from {usernames_file}")
            return usernames
        except FileNotFoundError:
            print(f"Fetcher:\tUsernames file not found: {usernames_file}")
            return []
    def fetch(self):
        if self._config['fetch']['clear']:
            stdout, stderr, code = self._shell.cmd(
                    f"rm -rf {self._path} && " +
                    f"mkdir {self._path}"
            )

        # Load usernames from file
        usernames = self._load_usernames()
        
        if not usernames:
            print("Fetcher:\tNo usernames loaded. Using original org-wide fetch.")
            self._fetch_org_wide()
        else:
            self._fetch_by_usernames(usernames)

    def _fetch_org_wide(self):
        """Original fetching logic that searches across all org repos."""
        # Don't paginate (GitHub(R)'s API paginates by default).
        page = 1
        while True:
            response = requests.get(self._url, headers=self._headers,
                                    params={'page' : page})
            if response.status_code != 200:
                print(f"bad response status code: {response.status_code}")
                break

            repos = response.json()
            if not repos:
                print(f"no json response")
                break

            print(response)

            for repo in repos:
                self._process_repo(repo)

            if 'Link' not in response.headers:
                break

            page += 1

    def _fetch_by_usernames(self, usernames):
        """Fetch repos for each username, filtering by milestone pattern."""
        for username in usernames:
            print(f"Fetcher:\tFetching repos for user: {username}")
            
            # Search for repos matching the milestone pattern and username
            repo_pattern = self._glob.replace('*', username)
            print(f"Fetcher:\tSearching for repos matching: {repo_pattern}")
            
            page = 1
            while True:
                response = requests.get(
                    self._url,
                    headers=self._headers,
                    params={'page': page}
                )
                
                if response.status_code != 200:
                    print(f"bad response status code: {response.status_code}")
                    break

                repos = response.json()
                if not repos:
                    break

                for repo in repos:
                    # Check if repo matches pattern for this username
                    if fnmatch.fnmatch(repo['name'], repo_pattern):
                        self._process_repo(repo)

                if 'Link' not in response.headers:
                    break

                page += 1

    def _process_repo(self, repo):
        """Process a single repo: check dates and clone if needed."""
        # Skip repos that are older than our specified minimum year/month.
        created_at = datetime.strptime(repo['created_at'],
                                       "%Y-%m-%dT%H:%M:%SZ")
        pushed_at = datetime.strptime(repo['pushed_at'],
                                      "%Y-%m-%dT%H:%M:%SZ")

        if (created_at.year < self._mindate.year and
            created_at.month < self._mindate.month):
            return

        if (pushed_at < self._push_mindate):
            return

        print(f'Fetcher:\tfetch:\tpushed_at after:\t{pushed_at}')

        if self._clone:
            # xxx log
            print(
                f'Fetcher:\tAttempting to clone {repo["name"]}'
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
                print(f"Fetch Error: \n{stderr}")

        else:
            # xxx log
            print(f'Fetcher:\tfetch:\t{repo["name"]}')
