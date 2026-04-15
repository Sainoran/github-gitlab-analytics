#!/usr/bin/env python3
import os
import json
from typing import Dict, Any, List, Tuple, Optional
import requests
from dotenv import load_dotenv

def github_request_ok(endpoint: str, token: str, base_url: str) -> Tuple[Optional[Any], bool]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    url = f"{base_url}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json(), True
        return None, False
    except Exception:
        return None, False

def gitlab_request_ok(endpoint: str, token: str, base_url: str) -> Tuple[Optional[Any], bool]:
    headers = {"PRIVATE-TOKEN": token}
    url = f"{base_url}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json(), True
        return None, False
    except Exception:
        return None, False

def count_filled_fields(profile: Dict[str, Any], fields: List[str]) -> int:
    filled = 0
    for field in fields:
        value = profile.get(field)
        if value is not None and value != "":
            filled += 1
    return filled

def get_repo_languages_ok(languages_url: str, token: str) -> Tuple[List[str], bool]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        resp = requests.get(languages_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return list(data.keys()), True
        return [], False
    except Exception:
        return [], False

def collect_github(token: str, base_url: str, errors: List[str]) -> Dict[str, Any]:
    result = {
        "username": None,
        "total_repos": 0,
        "total_stars": 0,
        "total_forks": 0,
        "most_popular_repo": None,
        "languages": [],
        "profile_filled": 0
    }
    user_data, ok = github_request_ok("user", token, base_url)
    if not ok:
        errors.append("github /user: не удалось загрузить профиль")
        return result
    result["username"] = user_data.get("login")
    result["profile_filled"] = count_filled_fields(user_data, ["login", "name", "bio", "email"])
    repos_data, ok = github_request_ok("user/repos", token, base_url)
    if not ok:
        errors.append("github /user/repos: не удалось загрузить репозитории")
        return result
    if not isinstance(repos_data, list):
        errors.append("github /user/repos: не удалось загрузить репозитории")
        return result
    result["total_repos"] = len(repos_data)
    stars_sum = 0
    forks_sum = 0
    max_stars = -1
    most_popular = None
    all_languages = set()
    for repo in repos_data:
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        stars_sum += stars
        forks_sum += forks
        if stars > max_stars:
            max_stars = stars
            most_popular = repo.get("name")
        lang_url = repo.get("languages_url")
        if lang_url:
            langs, lang_ok = get_repo_languages_ok(lang_url, token)
            if not lang_ok:
                repo_name = repo.get("name", "unknown")
                errors.append(f"github languages для {repo_name}: не удалось загрузить языки")
            else:
                all_languages.update(langs)
    result["total_stars"] = stars_sum
    result["total_forks"] = forks_sum
    result["most_popular_repo"] = most_popular
    result["languages"] = sorted(all_languages)
    return result

def collect_gitlab(token: str, base_url: str, errors: List[str]) -> Dict[str, Any]:
    result = {"username": None, "profile_filled": 0}
    user_data, ok = gitlab_request_ok("user", token, base_url)
    if not ok:
        errors.append("gitlab /user: не удалось загрузить профиль")
        return result
    result["username"] = user_data.get("username")
    result["profile_filled"] = count_filled_fields(user_data, ["username", "state", "location", "public_email"])
    return result

def main() -> None:
    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    gitlab_token = os.getenv("GITLAB_TOKEN")
    github_api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
    gitlab_api_url = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4")
    errors: List[str] = []
    if not github_token:
        errors.append("github /user: не удалось загрузить профиль")
        errors.append("github /user/repos: не удалось загрузить репозитории")
        github_data = {"username": None, "total_repos": 0, "total_stars": 0, "total_forks": 0, "most_popular_repo": None, "languages": [], "profile_filled": 0}
    else:
        github_data = collect_github(github_token, github_api_url, errors)
    if not gitlab_token:
        errors.append("gitlab /user: не удалось загрузить профиль")
        gitlab_data = {"username": None, "profile_filled": 0}
    else:
        gitlab_data = collect_gitlab(gitlab_token, gitlab_api_url, errors)
    output = {
        "github_username": github_data["username"],
        "gitlab_username": gitlab_data["username"],
        "total_repos": github_data["total_repos"],
        "total_stars": github_data["total_stars"],
        "total_forks": github_data["total_forks"],
        "most_popular_repo": github_data["most_popular_repo"],
        "languages": github_data["languages"],
        "github_profile_filled": github_data["profile_filled"],
        "gitlab_profile_filled": gitlab_data["profile_filled"],
        "errors": errors
    }
    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
