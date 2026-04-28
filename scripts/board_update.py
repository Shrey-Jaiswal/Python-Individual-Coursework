#!/usr/bin/env python3
"""
Sync Project v2 Status from issues.csv.

Required env:
  GITHUB_TOKEN
  GITHUB_OWNER
  GITHUB_REPO

Optional env:
    GITHUB_HOST (default: github.qmul.ac.uk, use github.com for GitHub.com)
  PROJECT_TITLE (default: Digital ID Coursework Board)
  PROJECT_OWNER_TYPE (user|org, default: user)
  CSV_PATH (default: issues.csv)
  DRY_RUN (true/false)
  ADD_MISSING (true/false, default: true)
"""

import csv
import json
import os
import sys
import urllib.error
import urllib.request


def env(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def api_base_for_host(host):
    host = host.lower()
    if host in {"github.com", "api.github.com"}:
        return "https://api.github.com"
    return f"https://{host}/api/v3"


def graphql_url_for_host(host):
    host = host.lower()
    if host in {"github.com", "api.github.com"}:
        return "https://api.github.com/graphql"
    return f"https://{host}/api/graphql"


def request_json(method, url, headers, payload=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body}") from exc


def rest_request(method, base_url, path, headers, payload=None):
    return request_json(method, f"{base_url}{path}", headers, payload)


def gql_request(url, headers, query, variables):
    payload = {"query": query, "variables": variables}
    data = request_json("POST", url, headers, payload)
    if not data:
        raise RuntimeError("Empty GraphQL response")
    if data.get("errors"):
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def gql_request_optional(url, headers, query, variables):
    payload = {"query": query, "variables": variables}
    return request_json("POST", url, headers, payload) or {}


def read_issues(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def normalize_title(value):
    if value is None:
        return ""
    return " ".join(value.strip().lower().split())


def list_issues(rest_base, headers, owner, repo):
    issues = {}
    page = 1
    while True:
        data = rest_request(
            "GET",
            rest_base,
            f"/repos/{owner}/{repo}/issues?state=all&per_page=100&page={page}",
            headers,
        )
        if not data:
            break
        for item in data:
            if "pull_request" in item:
                continue
            issues[item["title"]] = item
        if len(data) < 100:
            break
        page += 1
    return issues


def get_project_owner(gql_url, headers, owner_login, owner_type):
    def query_user():
        query = """
        query($login: String!) {
          user(login: $login) { id login projectsV2(first: 50) { nodes { id title url } } }
        }
        """
        result = gql_request_optional(gql_url, headers, query, {"login": owner_login})
        return (result.get("data") or {}).get("user")

    def query_org():
        query = """
        query($login: String!) {
          organization(login: $login) { id login projectsV2(first: 50) { nodes { id title url } } }
        }
        """
        result = gql_request_optional(gql_url, headers, query, {"login": owner_login})
        return (result.get("data") or {}).get("organization")

    if owner_type == "org":
        entity = query_org()
        if entity:
            return "org", entity
        entity = query_user()
        if entity:
            return "user", entity
    else:
        entity = query_user()
        if entity:
            return "user", entity
        entity = query_org()
        if entity:
            return "org", entity

    raise RuntimeError("Owner not found as user or org")


def get_project_by_title(entity, project_title):
    for project in entity["projectsV2"]["nodes"]:
        if project["title"] == project_title:
            return project
    titles = ", ".join(sorted(p["title"] for p in entity["projectsV2"]["nodes"]))
    raise RuntimeError(f"Project '{project_title}' not found. Available: {titles}")


def get_project_fields(gql_url, headers, project_id):
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2SingleSelectField { id name options { id name } }
              ... on ProjectV2FieldCommon { id name }
            }
          }
        }
      }
    }
    """
    data = gql_request(gql_url, headers, query, {"projectId": project_id})
    return data["node"]["fields"]["nodes"]


def ensure_status_field(fields):
    for field in fields:
        if field.get("name") == "Status" and field.get("options"):
            return field["id"], field["options"]
    raise RuntimeError("Status field not found in project")


def list_project_items(gql_url, headers, project_id):
    mapping = {}
    cursor = None
    while True:
        query = """
        query($projectId: ID!, $after: String) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: 100, after: $after) {
                nodes {
                  id
                                    content { ... on Issue { id number title state } }
                }
                pageInfo { hasNextPage endCursor }
              }
            }
          }
        }
        """
        data = gql_request(gql_url, headers, query, {"projectId": project_id, "after": cursor})
        items = data["node"]["items"]["nodes"]
        for item in items:
            content = item.get("content")
            if content and content.get("id"):
                                mapping[content["id"]] = {
                                        "item_id": item["id"],
                                        "number": content.get("number"),
                                        "state": content.get("state"),
                                        "title": content.get("title"),
                                }
        page_info = data["node"]["items"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
    return mapping


def reopen_issue(rest_base, headers, owner, repo, issue_number, dry_run):
    if dry_run:
        print(f"[dry-run] reopen issue: #{issue_number}")
        return None
    payload = {"state": "open"}
    data = rest_request("PATCH", rest_base, f"/repos/{owner}/{repo}/issues/{issue_number}", headers, payload)
    print(f"Reopened issue: #{data['number']} {data['title']}")
    return data


def add_item_to_project(gql_url, headers, project_id, content_id, dry_run):
    if dry_run:
        print(f"[dry-run] add item to project: {content_id}")
        return None
    mutation = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
        item { id }
      }
    }
    """
    data = gql_request(gql_url, headers, mutation, {"projectId": project_id, "contentId": content_id})
    return data["addProjectV2ItemById"]["item"]["id"]


def set_item_status(gql_url, headers, project_id, item_id, field_id, option_id, dry_run):
    if dry_run:
        print(f"[dry-run] set status for item: {item_id}")
        return
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: { projectId: $projectId, itemId: $itemId, fieldId: $fieldId, value: { singleSelectOptionId: $optionId } }) {
        projectV2Item { id }
      }
    }
    """
    gql_request(
        gql_url,
        headers,
        mutation,
        {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "optionId": option_id},
    )


def main():
    host = env("GITHUB_HOST", "github.qmul.ac.uk")
    owner = env("GITHUB_OWNER", required=True)
    repo = env("GITHUB_REPO", required=True)
    token = env("GITHUB_TOKEN", required=True)
    project_title = env("PROJECT_TITLE", "Digital ID Coursework Board")
    owner_type = env("PROJECT_OWNER_TYPE", "user").lower()
    csv_path = env("CSV_PATH", "issues.csv")
    dry_run = env("DRY_RUN", "false").lower() in {"1", "true", "yes"}
    add_missing = env("ADD_MISSING", "true").lower() in {"1", "true", "yes"}
    reset_all = env("RESET_ALL", "false").lower() in {"1", "true", "yes"}
    reopen_closed = env("REOPEN_CLOSED", "false").lower() in {"1", "true", "yes"}

    status_alias = {
        "backlog": "todo",
        "draft": "todo",
        "needs to be done": "todo",
    }

    rest_base = api_base_for_host(host)
    gql_url = graphql_url_for_host(host)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    issues = read_issues(csv_path)
    issue_map = list_issues(rest_base, headers, owner, repo)
    issue_map_normalized = {normalize_title(k): v for k, v in issue_map.items()}

    _, owner_entity = get_project_owner(gql_url, headers, owner, owner_type)
    project = get_project_by_title(owner_entity, project_title)
    print(f"Project URL: {project.get('url', project_title)}")

    fields = get_project_fields(gql_url, headers, project["id"])
    status_field_id, options = ensure_status_field(fields)
    option_by_name = {opt["name"].lower(): opt["id"] for opt in options if "id" in opt}

    project_items = list_project_items(gql_url, headers, project["id"])

    if reset_all:
        todo_option = option_by_name.get("todo")
        if not todo_option:
            print("Reset requested but no 'Todo' status option found.")
        else:
            for content_id, info in project_items.items():
                item_id = info.get("item_id")
                if item_id:
                    set_item_status(gql_url, headers, project["id"], item_id, status_field_id, todo_option, dry_run)
                number = info.get("number")
                state = info.get("state")
                if reopen_closed and number and state == "CLOSED":
                    reopen_issue(rest_base, headers, owner, repo, number, dry_run)
            print("Reset complete: set all items to Todo.")

    for issue in issues:
        title = issue.get("title", "").strip()
        if not title:
            continue
        status = issue.get("status", "Todo").strip().lower()
        status = status_alias.get(status, status)

        issue_data = issue_map.get(title)
        if not issue_data:
            issue_data = issue_map_normalized.get(normalize_title(title))
        if not issue_data:
            print(f"Skip missing issue: {title}")
            continue

        content_id = issue_data.get("node_id")
        if not content_id:
            print(f"Skip missing node_id: {title}")
            continue

        item_info = project_items.get(content_id)
        item_id = item_info.get("item_id") if item_info else None
        if not item_id:
            if not add_missing:
                print(f"Skip missing project item: {title}")
                continue
            item_id = add_item_to_project(gql_url, headers, project["id"], content_id, dry_run)
            if item_id:
                project_items[content_id] = {"item_id": item_id}

        option_id = option_by_name.get(status)
        if not option_id:
            print(f"Unknown status '{status}' for {title}")
            continue
        set_item_status(gql_url, headers, project["id"], item_id, status_field_id, option_id, dry_run)
        print(f"Set status for {title}: {status}")

    print("Board sync complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
