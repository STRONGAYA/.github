import os
import requests
import base64
from datetime import datetime

# GitHub API endpoint to list repositories in an organisation
REPOS_URL = "https://api.github.com/orgs/{org}/repos"

# GitHub API endpoint to get the contents of a file in a repository
FILE_URL = "https://api.github.com/repos/{org}/{repo}/contents/{path}"

# GitHub API endpoint to create or update a file in a repository
CREATE_OR_UPDATE_URL = "https://api.github.com/repos/{org}/{repo}/contents/{path}"

# GitHub API endpoint to trigger a workflow
WORKFLOW_DISPATCH_URL = "https://api.github.com/repos/{org}/{repo}/actions/workflows/{workflow_id}/dispatches"

# GitHub token for authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Organisation name
ORG_NAME = os.getenv("ORG_NAME")

# Copyright owner name
COPYRIGHT_OWNER = os.getenv("COPYRIGHT_OWNER")

# Current year
CURRENT_YEAR = datetime.now().year

# Headers for GitHub API requests
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# URL to fetch the Apache 2.0 licence text
APACHE_LICENCE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"

def get_repositories(org):
    response = requests.get(REPOS_URL.format(org=org), headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_file_contents(org, repo, path):
    response = requests.get(FILE_URL.format(org=org, repo=repo, path=path), headers=HEADERS)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()

def create_or_update_file(org, repo, path, content, message, sha=None):
    data = {
        "message": message,
        "content": content
    }
    if sha:
        data["sha"] = sha
    response = requests.put(CREATE_OR_UPDATE_URL.format(org=org, repo=repo, path=path), headers=HEADERS, json=data)
    response.raise_for_status()

def trigger_workflow(org, repo, workflow_id):
    data = {
        "ref": "main"  # Assuming the workflow should run on the main branch
    }
    response = requests.post(WORKFLOW_DISPATCH_URL.format(org=org, repo=repo, workflow_id=workflow_id), headers=HEADERS, json=data)
    response.raise_for_status()

def fetch_apache_licence():
    response = requests.get(APACHE_LICENCE_URL)
    response.raise_for_status()
    return response.text

def main():
    repos = get_repositories(ORG_NAME)
    apache_licence_text = fetch_apache_licence()

    for repo in repos:
        repo_name = repo["name"]
        licence_file = get_file_contents(ORG_NAME, repo_name, "LICENCE")
        license_file = get_file_contents(ORG_NAME, repo_name, "LICENSE")

        if licence_file is None and license_file is None:
            print(f"No LICENCE or LICENSE file found in {repo_name}, adding Apache 2.0 licence")
            # Encode the Apache 2.0 licence text to base64
            encoded_licence = base64.b64encode(apache_licence_text.encode("utf-8")).decode("utf-8")
            # Create the LICENCE file in the repository
            create_or_update_file(ORG_NAME, repo_name, "LICENCE", encoded_licence, "Add Apache 2.0 licence")
            continue

        if license_file is not None:
            # Rename LICENSE to LICENCE
            content = license_file["content"]
            sha = license_file["sha"]
            create_or_update_file(ORG_NAME, repo_name, "LICENCE", content, "Rename LICENSE to LICENCE", sha)
            print(f"Renamed LICENSE to LICENCE in {repo_name}")

        content = licence_file["content"]
        sha = licence_file["sha"]
        decoded_content = base64.b64decode(content).decode("utf-8")

        # Check if the year is not the current year and update it
        if f"{CURRENT_YEAR} {COPYRIGHT_OWNER}" not in decoded_content:
            # Update the licence content with the current year and copyright owner
            updated_content = decoded_content.replace(
                "[yyyy] [name of copyright owner]",
                f"{CURRENT_YEAR} {COPYRIGHT_OWNER}"
            )
        else:
            updated_content = decoded_content

        # Encode the updated content back to base64
        encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")

        # Update the file in the repository
        create_or_update_file(ORG_NAME, repo_name, "LICENCE", encoded_content, "Update licence with current year and copyright owner", sha)
        print(f"Updated LICENCE file in {repo_name}")

        # Check for the presence of release.yml and trigger it if it exists
        release_workflow = get_file_contents(ORG_NAME, repo_name, ".github/workflows/release.yml")
        if release_workflow is not None:
            print(f"Triggering release.yml workflow in {repo_name}")
            trigger_workflow(ORG_NAME, repo_name, "release.yml")

if __name__ == "__main__":
    main()