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

class NewFetcher:
    def __init__(self, config):
        self._shell = Shell()
        self._config = config

        self._dotenv = ".env"
        load_dotenv(self._dotenv)

        # self._milestone = milestone
        # print(f"Fetcher:\tmilestone:\t{self._milestone}")

        # # Milestone with Professor's name appended.
        # self._pmilestone = self._milestone + f"-{self._config['prof']}"
        # print(f"Fetcher:\tprofessor milestone:\t{self._pmilestone}")

        # # Format "milestoneX" as "milestone-X".
        # self._fmilestone = util.fmt_milestone(milestone)
        # print(f"Fetcher:\tformatted milestone:\t{self._fmilestone}")

        # self._init_timestamp(date)
        # self._init_req()
        # self._init_path(path)

        # self._clone = self._config['clone']

    def fetch(self):
      github_token = os.getenv('PAT')
      org_name = self._config['org']
      
      auth = Auth.Token(github_token)
      # Public Web Github
      github_instance = Github(auth=auth)
      
      search_query = f"milestone-2 org:{org_name} in:name"
      repos = github_instance.search_repositories(query=search_query)
      
			
      # repositories = github_instance.get_organization(org_name).get_repos(sort="full_name")
      
      github_instance.close()

