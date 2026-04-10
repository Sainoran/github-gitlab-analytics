#!/usr/bin/env python3
"""
Скрипт собирает данные о пользователе с GitHub и GitLab,
формирует аналитическую сводку в файле result.json.
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_API_URL = GITHUB_API_URL.rstrip("/")
GITLAB_API_URL = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4")
GITLAB_API_URL = GITLAB_API_URL.rstrip("/")


def safe_request(
    url: str, headers: Dict
) -> Tuple[Optional[Any], Optional[str]]:
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def github_get_all_repos(token: str) -> Tuple[List[Dict], List[str]]:
    repos = []
    errors = []
    page = 1
    per_page = 100
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    while True:
        url = f"{GITHUB_API_URL}/user/repos"
        params = {"per_page": per_page, "page": page, "sort": "updated"}
        try:
            resp = requests.get(
                url, headers=headers, params=params, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        except requests.exceptions.RequestException as e:
            errors.append(f"github /user/repos: {str(e)}")
            break
    return repos, errors


def get_github_languages(
    languages_url: str, token: str
) -> Tuple[Dict, Optional[str]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return safe_request(languages_url, headers)


def count_github_profile_filled(profile: Dict) -> int:
    fields = ["login", "name", "bio", "email"]
    count = 0
    for field in fields:
        value = profile.get(field)
        if value is not None and value != "":
            count += 1
    return count


def count_gitlab_profile_filled(profile: Dict) -> int:
    fields = ["username", "state", "location", "public_email"]
    count = 0
    for field in fields:
        value = profile.get(field)
        if value is not None and value != "":
            count += 1
    return count


def main():
    errors = []

    # --- GitHub ---
    github_username = None
    github_profile_filled = 0
    total_repos = 0
    total_stars = 0
    total_forks = 0
    most_popular_repo = None
    languages = []

    if not GITHUB_TOKEN:
        errors.append("github: отсутствует GITHUB_TOKEN в .env")
    else:
        github_headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        profile_github, err_github_profile = safe_request(
            f"{GITHUB_API_URL}/user", github_headers
        )
        if err_github_profile:
            errors.append(f"github /user: {err_github_profile}")
        else:
            github_username = profile_github.get("login")
            github_profile_filled = count_github_profile_filled(profile_github)

        repos, repos_errors = github_get_all_repos(GITHUB_TOKEN)
        errors.extend(repos_errors)

        if repos_errors and not repos:
            pass
        else:
            total_repos = len(repos)
            total_stars = sum(r.get("stargazers_count", 0) for r in repos)
            total_forks = sum(r.get("forks_count", 0) for r in repos)

            max_stars = -1
            for repo in repos:
                stars = repo.get("stargazers_count", 0)
                if stars > max_stars:
                    max_stars = stars
                    most_popular_repo = repo.get("name")

            language_set = set()
            for repo in repos:
                lang_url = repo.get("languages_url")
                if not lang_url:
                    continue
                langs_data, lang_err = get_github_languages(
                    lang_url, GITHUB_TOKEN
                )
                if lang_err:
                    errors.append(
                        f"github languages for {repo.get('name')}: {lang_err}"
                    )
                else:
                    language_set.update(langs_data.keys())
            languages = sorted(language_set)

    # --- GitLab ---
    gitlab_username = None
    gitlab_profile_filled = 0

    if not GITLAB_TOKEN:
        errors.append("gitlab: отсутствует GITLAB_TOKEN в .env")
    else:
        gitlab_headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
        profile_gitlab, err_gitlab_profile = safe_request(
            f"{GITLAB_API_URL}/user", gitlab_headers
        )
        if err_gitlab_profile:
            errors.append(f"gitlab /user: {err_gitlab_profile}")
        else:
            gitlab_username = profile_gitlab.get("username")
            gitlab_profile_filled = count_gitlab_profile_filled(profile_gitlab)

    result = {
        "github_username": github_username,
        "gitlab_username": gitlab_username,
        "total_repos": total_repos,
        "total_stars": total_stars,
        "total_forks": total_forks,
        "most_popular_repo": most_popular_repo,
        "languages": languages,
        "github_profile_filled": github_profile_filled,
        "gitlab_profile_filled": gitlab_profile_filled,
        "errors": errors,
    }

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("result.json успешно создан")


if __name__ == "__main__":
    main()
