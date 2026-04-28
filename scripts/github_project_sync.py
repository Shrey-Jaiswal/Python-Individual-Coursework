#!/usr/bin/env python3
"""
Local-only helper to create issues from issues.csv and add them to a Project v2 board.
Do not commit tokens. Set them in environment variables when running.
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
    data = request_json("POST", url, headers, payload)
    if not data:
        return {"data": None, "errors": [{"message": "Empty GraphQL response"}]}
    return data


def read_issues(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def list_labels(rest_base, headers, owner, repo):
    labels = set()
    page = 1
    while True:
        data = rest_request(
            "GET",
            rest_base,
            f"/repos/{owner}/{repo}/labels?per_page=100&page={page}",
            headers,
        )
        if not data:
            break
        labels.update(item["name"] for item in data)
        if len(data) < 100:
            break
        page += 1
    return labels


def ensure_labels(rest_base, headers, owner, repo, label_names, dry_run):
    existing = list_labels(rest_base, headers, owner, repo)
    for label in sorted(label_names):
        if label in existing:
            continue
        if dry_run:
            print(f"[dry-run] create label: {label}")
            continue
        payload = {"name": label, "color": "0366d6"}
        rest_request("POST", rest_base, f"/repos/{owner}/{repo}/labels", headers, payload)
        print(f"Created label: {label}")


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


def create_issue(rest_base, headers, owner, repo, title, body, labels, dry_run):
    if dry_run:
        print(f"[dry-run] create issue: {title}")
        return None
    payload = {"title": title, "body": body, "labels": labels}
    data = rest_request("POST", rest_base, f"/repos/{owner}/{repo}/issues", headers, payload)
    print(f"Created issue: #{data['number']} {data['title']}")
    return data


def update_issue(rest_base, headers, owner, repo, issue_number, title, body, labels, dry_run):
    if dry_run:
        print(f"[dry-run] update issue: #{issue_number} {title}")
        return None
    payload = {"title": title, "body": body, "labels": labels}
    data = rest_request("PATCH", rest_base, f"/repos/{owner}/{repo}/issues/{issue_number}", headers, payload)
    print(f"Updated issue: #{data['number']} {data['title']}")
    return data


def reopen_issue(rest_base, headers, owner, repo, issue_number, dry_run):
    if dry_run:
        print(f"[dry-run] reopen issue: #{issue_number}")
        return None
    payload = {"state": "open"}
    data = rest_request("PATCH", rest_base, f"/repos/{owner}/{repo}/issues/{issue_number}", headers, payload)
    print(f"Reopened issue: #{data['number']} {data['title']}")
    return data


def get_project_owner(gql_url, headers, owner_login, owner_type):
    def query_user():
        query = """
        query($login: String!) {
          user(login: $login) { id login projectsV2(first: 50) { nodes { id title } } }
        }
        """
        result = gql_request_optional(gql_url, headers, query, {"login": owner_login})
        data = result.get("data") or {}
        return data.get("user")

    def query_org():
        query = """
        query($login: String!) {
          organization(login: $login) { id login projectsV2(first: 50) { nodes { id title } } }
        }
        """
        result = gql_request_optional(gql_url, headers, query, {"login": owner_login})
        data = result.get("data") or {}
        return data.get("organization")

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


def get_or_create_project(gql_url, headers, owner_id, project_title, dry_run):
    query = """
    query($ownerId: ID!) {
      node(id: $ownerId) {
        ... on User { projectsV2(first: 50) { nodes { id title } } }
        ... on Organization { projectsV2(first: 50) { nodes { id title } } }
      }
    }
    """
    data = gql_request(gql_url, headers, query, {"ownerId": owner_id})
    node = data["node"]
    projects = node["projectsV2"]["nodes"]
    for project in projects:
        if project["title"] == project_title:
            return project["id"], False
    if dry_run:
        print(f"[dry-run] create project: {project_title}")
        return None, True
    mutation = """
    mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: { ownerId: $ownerId, title: $title }) {
        projectV2 { id title }
      }
    }
    """
    data = gql_request(gql_url, headers, mutation, {"ownerId": owner_id, "title": project_title})
    return data["createProjectV2"]["projectV2"]["id"], True


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


def get_project_summary(gql_url, headers, project_id):
        query = """
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 { id title url number }
            }
        }
        """
        data = gql_request(gql_url, headers, query, {"projectId": project_id})
        return data["node"]


def ensure_timestamp_fields(gql_url, headers, project_id, dry_run):
    fields = get_project_fields(gql_url, headers, project_id)
    existing = {field.get("name", "").strip().lower() for field in fields}
    targets = ["Created", "Updated", "Closed"]
    missing = [name for name in targets if name.lower() not in existing]
    if not missing:
        return []
    created = []
    for name in missing:
        if dry_run:
            print(f"[dry-run] create {name} timestamp field")
            continue
        mutation = """
        mutation($projectId: ID!, $name: String!, $dataType: ProjectV2FieldType!) {
          createProjectV2Field(input: { projectId: $projectId, name: $name, dataType: $dataType }) {
            projectV2Field { ... on ProjectV2FieldCommon { id name } }
          }
        }
        """
        data = gql_request(
            gql_url,
            headers,
            mutation,
            {"projectId": project_id, "name": name, "dataType": "DATE"},
        )
        field = data.get("createProjectV2Field", {}).get("projectV2Field")
        if field:
            created.append(field)
            print(f"Created {name} timestamp field")
    return created


def ensure_status_field(gql_url, headers, project_id, dry_run):
    fields = get_project_fields(gql_url, headers, project_id)
    for field in fields:
        if field.get("name") == "Status" and field.get("options"):
            return field["id"], field["options"], False
    options = [
        {"name": "Todo", "color": "GRAY"},
        {"name": "In Progress", "color": "BLUE"},
        {"name": "Done", "color": "GREEN"},
    ]
    if dry_run:
        print("[dry-run] create Status field with options")
        return None, options, True
    mutation = """
    mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
      createProjectV2Field(input: { projectId: $projectId, name: $name, dataType: SINGLE_SELECT, singleSelectOptions: $options }) {
        projectV2Field {
          ... on ProjectV2SingleSelectField { id name options { id name } }
        }
      }
    }
    """
    data = gql_request(
        gql_url,
        headers,
        mutation,
        {"projectId": project_id, "name": "Status", "options": options},
    )
    field = data["createProjectV2Field"]["projectV2Field"]
    return field["id"], field["options"], True


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
                  content { ... on Issue { id title } }
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
                mapping[content["id"]] = item["id"]
        page_info = data["node"]["items"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
    return mapping


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
    verbose = env("VERBOSE", "false").lower() in {"1", "true", "yes"}
    update_existing = env("UPDATE_EXISTING", "false").lower() in {"1", "true", "yes"}
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
    label_names = set()
    for issue in issues:
        labels = [label.strip() for label in issue.get("labels", "").split(";") if label.strip()]
        label_names.update(labels)

    ensure_labels(rest_base, headers, owner, repo, label_names, dry_run)

    existing = list_issues(rest_base, headers, owner, repo)
    created_or_existing = []
    for issue in issues:
        title = issue["title"].strip()
        body = issue.get("body", "").strip()
        labels = [label.strip() for label in issue.get("labels", "").split(";") if label.strip()]
        if title in existing:
            item = existing[title]
            print(f"Issue exists: #{item['number']} {title}")
            if update_existing:
                update_issue(
                    rest_base,
                    headers,
                    owner,
                    repo,
                    item["number"],
                    title,
                    body,
                    labels,
                    dry_run,
                )
                if verbose:
                    print(f"Updated issue body for: {title}")
            if reopen_closed and item.get("state") == "closed":
                reopen_issue(rest_base, headers, owner, repo, item["number"], dry_run)
            created_or_existing.append(item)
            continue
        item = create_issue(rest_base, headers, owner, repo, title, body, labels, dry_run)
        if item:
            created_or_existing.append(item)

    if dry_run:
        print("[dry-run] skip project sync")
        return

    owner_kind, owner_entity = get_project_owner(gql_url, headers, owner, owner_type)
    project_id, created = get_or_create_project(gql_url, headers, owner_entity["id"], project_title, dry_run)
    if created:
        print(f"Project created: {project_title}")
    else:
        print(f"Using existing project: {project_title}")

    summary = get_project_summary(gql_url, headers, project_id)
    if summary and summary.get("url"):
        print(f"Project URL: {summary['url']}")

    ensure_timestamp_fields(gql_url, headers, project_id, dry_run)

    status_field_id, options, _ = ensure_status_field(gql_url, headers, project_id, dry_run)
    option_by_name = {opt["name"].lower(): opt["id"] for opt in options if "id" in opt}

    project_items = list_project_items(gql_url, headers, project_id)

    for issue in issues:
        title = issue["title"].strip()
        status = issue.get("status", "Backlog").strip().lower()
        status = status_alias.get(status, status)
        issue_data = existing.get(title)
        if not issue_data:
            for created in created_or_existing:
                if created.get("title") == title:
                    issue_data = created
                    break
        if not issue_data:
            print(f"Skip project add, missing issue: {title}")
            continue
        content_id = issue_data.get("node_id")
        if not content_id:
            print(f"Skip project add, missing node_id: {title}")
            continue
        item_id = project_items.get(content_id)
        if not item_id:
            item_id = add_item_to_project(gql_url, headers, project_id, content_id, dry_run)
            if item_id:
                project_items[content_id] = item_id
                if verbose:
                    print(f"Added to project: {title}")
        if not status_field_id:
            continue
        option_id = option_by_name.get(status)
        if not option_id:
            option_id = next(iter(option_by_name.values()), None)
        if option_id and item_id:
            set_item_status(gql_url, headers, project_id, item_id, status_field_id, option_id, dry_run)
            if verbose:
                print(f"Set status for {title}: {status}")

    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
