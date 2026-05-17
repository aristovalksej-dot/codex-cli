"""GitHub integration tools — clone, view, search repos."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import httpx

from codex_cli.tools.base import Tool


class CloneRepoTool(Tool):
    name = "clone_repo"
    description = (
        "Clone a Git repository to the local filesystem. "
        "Supports GitHub, GitLab, Bitbucket, and any Git URL."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": (
                    "Repository URL or shorthand (e.g. 'https://github.com/user/repo.git' "
                    "or 'user/repo' for GitHub)"
                ),
            },
            "destination": {
                "type": "string",
                "description": "Local path to clone into (optional, defaults to repo name in cwd)",
            },
            "branch": {
                "type": "string",
                "description": "Branch to clone (optional, defaults to default branch)",
            },
            "depth": {
                "type": "integer",
                "description": "Shallow clone depth (optional, 0 = full clone)",
            },
        },
        "required": ["url"],
    }

    async def execute(
        self,
        url: str,
        destination: str = "",
        branch: str = "",
        depth: int = 0,
        **_: Any,
    ) -> str:
        import asyncio

        if re.match(r"^[\w\-]+/[\w\-\.]+$", url):
            url = f"https://github.com/{url}.git"
        elif not url.startswith(("http://", "https://", "git@", "ssh://")):
            url = f"https://github.com/{url}.git"

        if not destination:
            repo_name = url.rstrip("/").rstrip(".git").split("/")[-1]
            destination = os.path.join(os.getcwd(), repo_name)

        cmd_parts = ["git", "clone"]
        if branch:
            cmd_parts.extend(["--branch", branch])
        if depth > 0:
            cmd_parts.extend(["--depth", str(depth)])
        cmd_parts.extend([url, destination])

        cmd = " ".join(cmd_parts)

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
        except asyncio.TimeoutError:
            return f"Error: Clone timed out after 300s for {url}"
        except Exception as e:
            return f"Error cloning repo: {e}"

        if process.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            return f"Error cloning {url}:\n{err}"

        dest_path = Path(destination).resolve()
        return f"Successfully cloned {url} to {dest_path}"


class GitCommandTool(Tool):
    name = "git_command"
    description = (
        "Run a git command in a repository. "
        "Supports all git operations: status, log, diff, commit, push, pull, branch, etc."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "args": {
                "type": "string",
                "description": "Git command arguments (e.g. 'status', 'log --oneline -10', 'diff HEAD~1')",
            },
            "repo_path": {
                "type": "string",
                "description": "Path to the git repository (optional, defaults to cwd)",
            },
        },
        "required": ["args"],
    }

    async def execute(self, args: str, repo_path: str = "", **_: Any) -> str:
        import asyncio

        cwd = repo_path or os.getcwd()
        cmd = f"git {args}"
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        except asyncio.TimeoutError:
            return f"Error: git command timed out\nCommand: {cmd}"
        except Exception as e:
            return f"Error: {e}"

        result_parts = [f"$ git {args}"]
        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if stdout_text:
            if len(stdout_text) > 50000:
                stdout_text = stdout_text[:25000] + "\n...[truncated]...\n" + stdout_text[-25000:]
            result_parts.append(stdout_text)
        if stderr_text and process.returncode != 0:
            result_parts.append(f"STDERR: {stderr_text}")
        if not stdout_text and not stderr_text:
            result_parts.append("(no output)")

        return "\n".join(result_parts)


class GitHubRepoInfoTool(Tool):
    name = "github_repo_info"
    description = (
        "Get information about a GitHub repository: description, stars, forks, "
        "language, recent commits, open issues, etc."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format (e.g. 'facebook/react')",
            },
        },
        "required": ["repo"],
    }

    async def execute(self, repo: str, **_: Any) -> str:
        api_url = f"https://api.github.com/repos/{repo}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(api_url, headers=headers)
                if resp.status_code == 404:
                    return f"Repository not found: {repo}"
                resp.raise_for_status()
                data = resp.json()

                info_lines = [
                    f"Repository: {data['full_name']}",
                    f"Description: {data.get('description', 'N/A')}",
                    f"Language: {data.get('language', 'N/A')}",
                    f"Stars: {data.get('stargazers_count', 0):,}",
                    f"Forks: {data.get('forks_count', 0):,}",
                    f"Open Issues: {data.get('open_issues_count', 0):,}",
                    f"Default Branch: {data.get('default_branch', 'main')}",
                    f"Created: {data.get('created_at', 'N/A')}",
                    f"Last Updated: {data.get('updated_at', 'N/A')}",
                    f"Clone URL: {data.get('clone_url', '')}",
                    f"Homepage: {data.get('homepage', 'N/A')}",
                    f"License: {data.get('license', {}).get('name', 'N/A') if data.get('license') else 'N/A'}",
                    f"Topics: {', '.join(data.get('topics', [])) or 'N/A'}",
                ]

                commits_resp = await client.get(
                    f"{api_url}/commits",
                    headers=headers,
                    params={"per_page": 5},
                )
                if commits_resp.status_code == 200:
                    commits = commits_resp.json()
                    info_lines.append("\nRecent Commits:")
                    for c in commits:
                        sha = c["sha"][:7]
                        msg = c["commit"]["message"].split("\n")[0][:80]
                        author = c["commit"]["author"]["name"]
                        info_lines.append(f"  {sha} {msg} ({author})")

                return "\n".join(info_lines)
        except Exception as e:
            return f"Error fetching repo info: {e}"


class GitHubSearchTool(Tool):
    name = "github_search"
    description = (
        "Search GitHub repositories, code, issues, or users. "
        "Returns top results with links and descriptions."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "search_type": {
                "type": "string",
                "enum": ["repositories", "code", "issues", "users"],
                "description": "Type of search (default: repositories)",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results (default: 10, max: 30)",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        search_type: str = "repositories",
        num_results: int = 10,
        **_: Any,
    ) -> str:
        num_results = min(max(num_results, 1), 30)
        api_url = f"https://api.github.com/search/{search_type}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    api_url,
                    headers=headers,
                    params={"q": query, "per_page": num_results},
                )
                resp.raise_for_status()
                data = resp.json()

            total = data.get("total_count", 0)
            items = data.get("items", [])

            if not items:
                return f"No {search_type} found for: {query}"

            lines = [f"GitHub {search_type} search: '{query}' ({total:,} total results)\n"]

            for i, item in enumerate(items, 1):
                if search_type == "repositories":
                    lines.append(
                        f"  {i}. {item['full_name']} ⭐{item.get('stargazers_count', 0):,}\n"
                        f"     {item.get('description', '')[:100]}\n"
                        f"     {item['html_url']}"
                    )
                elif search_type == "code":
                    lines.append(
                        f"  {i}. {item['repository']['full_name']}: {item['path']}\n"
                        f"     {item['html_url']}"
                    )
                elif search_type == "issues":
                    state = item.get("state", "")
                    lines.append(
                        f"  {i}. [{state}] {item['title'][:80]}\n"
                        f"     {item['html_url']}"
                    )
                elif search_type == "users":
                    lines.append(
                        f"  {i}. {item['login']} — {item['html_url']}"
                    )

            return "\n".join(lines)
        except Exception as e:
            return f"Error searching GitHub: {e}"
