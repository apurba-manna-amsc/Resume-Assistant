"""GitHub API client for fetching public repository README content."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, Optional, Tuple

import requests

from resume_assistant.core.errors import AppError, GitHubApiError, github_error_from_response

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]


class GitHubRepositoryClient:
    """Fetches README bodies from a user's public GitHub repositories."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def fetch_readme_contents(
        self,
        username: str,
        token: str = "",
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Dict[str, str]:
        """
        Return ``{repo_name: readme_text}`` for repos that have a README.

        ``on_progress(current, total, repo_name)`` is called after each repo is processed.
        """
        if not username.strip():
            return {}

        headers = {"Authorization": f"token {token}"} if token else {}
        project_details: Dict[str, str] = {}

        try:
            repos = self._list_repositories(username, headers)
            if not repos:
                return {}

            total = len(repos)

            def fetch_one(repo: dict) -> Tuple[str, Optional[str]]:
                return self._fetch_repository_readme(username, repo, headers)

            max_workers = min(32, (os.cpu_count() or 1) + 4)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(fetch_one, repo): repo for repo in repos}
                for i, future in enumerate(as_completed(futures), start=1):
                    repo_name, content = future.result()
                    if content:
                        project_details[repo_name] = content
                    if on_progress:
                        on_progress(i, total, repo_name)

            return project_details

        except GitHubApiError:
            raise
        except requests.exceptions.RequestException as exc:
            raise GitHubApiError(
                "Could not reach GitHub. Check your internet connection and try again.",
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise GitHubApiError(
                "An unexpected error occurred while fetching GitHub projects.",
                detail=str(exc),
            ) from exc

    def _list_repositories(self, username: str, headers: dict) -> list:
        repos: list = []
        page = 1
        while True:
            url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
            res = requests.get(url, headers=headers, timeout=self.timeout)
            if res.status_code != 200:
                raise github_error_from_response(res, username)
            data = res.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return repos

    def _fetch_repository_readme(
        self, username: str, repo: dict, headers: dict
    ) -> Tuple[str, Optional[str]]:
        try:
            repo_name = repo["name"]
            default_branch = repo.get("default_branch", "main")
            contents_url = (
                f"https://api.github.com/repos/{username}/{repo_name}"
                f"/contents?ref={default_branch}"
            )
            res = requests.get(contents_url, headers=headers, timeout=self.timeout)
            if res.status_code != 200:
                return repo_name, None

            files = res.json()
            readme_file = next(
                (f for f in files if f["name"].lower().startswith("readme")),
                None,
            )
            if readme_file and "download_url" in readme_file:
                readme_res = requests.get(
                    readme_file["download_url"], headers=headers, timeout=self.timeout
                )
                readme_res.raise_for_status()
                return repo_name, readme_res.text
        except requests.exceptions.RequestException as exc:
            logger.debug("README fetch failed for %s: %s", repo.get("name"), exc)
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("Unexpected README payload for %s: %s", repo.get("name"), exc)
        return repo.get("name", "unknown"), None
