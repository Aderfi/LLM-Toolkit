import os
import shlex
import shutil
import subprocess

from llmtools.core import backup_file, resolve_safe_path, tool

# Force stable, English, machine-readable git output regardless of system locale.
_GIT_ENV = {**os.environ, "LC_ALL": "C", "LANG": "C"}


def _run_git(args, repo):
    if shutil.which("git") is None:
        return "Error: 'git' binary not found."
    rp = resolve_safe_path(repo)
    r = subprocess.run(["git", "-C", rp, *args], capture_output=True, text=True, env=_GIT_ENV)
    return (r.stdout + r.stderr).strip() or "(no output)"


def _run_gh(args, repo):
    if shutil.which("gh") is None:
        return "Error: GitHub CLI 'gh' not found (needed for releases)."
    rp = resolve_safe_path(repo)
    r = subprocess.run(["gh", *args], capture_output=True, text=True, cwd=rp, env=_GIT_ENV)
    return (r.stdout + r.stderr).strip() or "(no output)"


# --------------------------------------------------------------------------- #
# Escape hatch: run ANY git subcommand not wrapped below.
# --------------------------------------------------------------------------- #
@tool
def git_run(args: str, repo: str = ".") -> str:
    """Run an arbitrary git command (escape hatch for anything not wrapped).

    Args:
        args: The git arguments as a string, e.g. 'log --graph --oneline -5'.
        repo: Repository path.
    """
    return _run_git(shlex.split(args), repo)


# --------------------------------------------------------------------------- #
# Repository setup
# --------------------------------------------------------------------------- #
@tool
def git_init(repo: str = ".") -> str:
    """Initialize a git repository.

    Args:
        repo: Directory to init.
    """
    return _run_git(["init"], repo)


@tool
def git_clone(url: str, dest: str) -> str:
    """Clone a repository into a destination directory (must be inside allowed roots).

    Args:
        url: Repository URL.
        dest: Destination directory path.
    """
    dp = resolve_safe_path(dest)
    if shutil.which("git") is None:
        return "Error: 'git' binary not found."
    r = subprocess.run(["git", "clone", url, dp], capture_output=True, text=True, env=_GIT_ENV)
    return (r.stdout + r.stderr).strip() or "(no output)"


# --------------------------------------------------------------------------- #
# Inspection
# --------------------------------------------------------------------------- #
@tool
def git_status(repo: str = ".") -> str:
    """Show git working-tree status.

    Args:
        repo: Repository path.
    """
    return _run_git(["status"], repo)


@tool
def git_diff(target: str = "", repo: str = ".") -> str:
    """Show a git diff. Empty target = unstaged changes; 'staged' = staged; or a ref/range.

    Args:
        target: '' for unstaged, 'staged' for staged, or a ref/range like 'HEAD~1'.
        repo: Repository path.
    """
    if target == "staged":
        return _run_git(["diff", "--staged"], repo)
    args = ["diff"] + ([target] if target else [])
    return _run_git(args, repo)


@tool
def git_log(repo: str = ".", count: int = 10) -> str:
    """Show recent commit log (oneline).

    Args:
        repo: Repository path.
        count: Number of commits.
    """
    return _run_git(["log", f"-{count}", "--oneline"], repo)


@tool
def git_show(ref: str = "HEAD", repo: str = ".") -> str:
    """Show a commit / object (message + diff).

    Args:
        ref: Commit-ish or object, e.g. 'HEAD', a SHA, or 'v1.0'.
        repo: Repository path.
    """
    return _run_git(["show", ref], repo)


@tool
def git_blame(path: str, repo: str = ".") -> str:
    """Show line-by-line authorship for a file.

    Args:
        path: File path relative to the repo.
        repo: Repository path.
    """
    return _run_git(["blame", path], repo)


@tool
def git_reflog(repo: str = ".", count: int = 20) -> str:
    """Show the reference log (recent HEAD movements).

    Args:
        repo: Repository path.
        count: Number of entries.
    """
    return _run_git(["reflog", f"-{count}"], repo)


# --------------------------------------------------------------------------- #
# Staging / committing / undoing
# --------------------------------------------------------------------------- #
@tool
def git_add(pathspec: str = ".", repo: str = ".") -> str:
    """Stage files.

    Args:
        pathspec: Files/globs to stage.
        repo: Repository path.
    """
    out = _run_git(["add", pathspec], repo)
    return out if out != "(no output)" else "Staged."


@tool
def git_commit(message: str, repo: str = ".") -> str:
    """Create a commit.

    Args:
        message: Commit message.
        repo: Repository path.
    """
    return _run_git(["commit", "-m", message], repo)


@tool
def git_reset(mode: str = "mixed", ref: str = "HEAD", repo: str = ".") -> str:
    """Reset current HEAD to a ref.

    Args:
        mode: 'soft', 'mixed', or 'hard'.
        ref: Target ref, e.g. 'HEAD~1'.
        repo: Repository path.
    """
    flag = {"soft": "--soft", "mixed": "--mixed", "hard": "--hard"}.get(mode, "--mixed")
    return _run_git(["reset", flag, ref], repo)


@tool
def git_restore(path: str, staged: bool = False, repo: str = ".") -> str:
    """Restore file(s) in the working tree, optionally unstaging.

    Args:
        path: Pathspec to restore.
        staged: If true, unstage (restore --staged) instead of discarding changes.
        repo: Repository path.
    """
    args = ["restore"] + (["--staged"] if staged else []) + [path]
    return _run_git(args, repo) or "Restored."


@tool
def git_rm(path: str, cached: bool = False, repo: str = ".") -> str:
    """Remove file(s) from the index (and optionally the working tree).

    Args:
        path: Pathspec to remove.
        cached: If true, only untrack (keep on disk).
        repo: Repository path.
    """
    args = ["rm"] + (["--cached"] if cached else []) + [path]
    return _run_git(args, repo)


@tool
def git_clean(repo: str = ".", directories: bool = False) -> str:
    """Remove untracked files (force). Add directories=True to also remove dirs.

    Args:
        repo: Repository path.
        directories: Also remove untracked directories.
    """
    args = ["clean", "-f"] + (["-d"] if directories else [])
    return _run_git(args, repo)


@tool
def git_revert(commit: str, repo: str = ".") -> str:
    """Revert a commit by creating a new inverse commit (no editor).

    Args:
        commit: Commit-ish to revert.
        repo: Repository path.
    """
    return _run_git(["revert", "--no-edit", commit], repo)


@tool
def git_stash(action: str = "push", repo: str = ".") -> str:
    """Manage the stash.

    Args:
        action: 'push', 'pop', 'list', 'apply', 'drop', or 'clear'.
        repo: Repository path.
    """
    return _run_git(["stash", action], repo)


# --------------------------------------------------------------------------- #
# Branching / integrating
# --------------------------------------------------------------------------- #
@tool
def git_branch(repo: str = ".") -> str:
    """List branches (local + remote).

    Args:
        repo: Repository path.
    """
    return _run_git(["branch", "-a"], repo)


@tool
def git_create_branch(name: str, repo: str = ".") -> str:
    """Create and switch to a new branch.

    Args:
        name: New branch name.
        repo: Repository path.
    """
    return _run_git(["switch", "-c", name], repo)


@tool
def git_checkout(ref: str, repo: str = ".") -> str:
    """Check out a branch, tag, or commit.

    Args:
        ref: Branch/tag/commit to check out.
        repo: Repository path.
    """
    return _run_git(["checkout", ref], repo)


@tool
def git_delete_branch(name: str, force: bool = False, repo: str = ".") -> str:
    """Delete a local branch.

    Args:
        name: Branch name.
        force: Force deletion (-D) even if unmerged.
        repo: Repository path.
    """
    return _run_git(["branch", "-D" if force else "-d", name], repo)


@tool
def git_rename_branch(old: str, new: str, repo: str = ".") -> str:
    """Rename a branch.

    Args:
        old: Current branch name.
        new: New branch name.
        repo: Repository path.
    """
    return _run_git(["branch", "-m", old, new], repo)


@tool
def git_merge(branch: str, repo: str = ".") -> str:
    """Merge a branch into the current branch.

    Args:
        branch: Branch to merge in.
        repo: Repository path.
    """
    return _run_git(["merge", branch], repo)


@tool
def git_rebase(onto: str, repo: str = ".") -> str:
    """Rebase the current branch onto another ref (non-interactive).

    Args:
        onto: Ref to rebase onto.
        repo: Repository path.
    """
    return _run_git(["rebase", onto], repo)


@tool
def git_cherry_pick(commit: str, repo: str = ".") -> str:
    """Cherry-pick a commit onto the current branch.

    Args:
        commit: Commit-ish to cherry-pick.
        repo: Repository path.
    """
    return _run_git(["cherry-pick", commit], repo)


# --------------------------------------------------------------------------- #
# Tags
# --------------------------------------------------------------------------- #
@tool
def git_tag_list(repo: str = ".") -> str:
    """List tags.

    Args:
        repo: Repository path.
    """
    return _run_git(["tag", "--list"], repo)


@tool
def git_tag_create(name: str, message: str = "", ref: str = "", repo: str = ".") -> str:
    """Create a tag (annotated if a message is given).

    Args:
        name: Tag name, e.g. 'v1.0.0'.
        message: Annotation message (empty = lightweight tag).
        ref: Commit-ish to tag (empty = HEAD).
        repo: Repository path.
    """
    args = ["tag"]
    if message:
        args += ["-a", name, "-m", message]
    else:
        args += [name]
    if ref:
        args += [ref]
    return _run_git(args, repo) or f"Tag {name} created."


@tool
def git_tag_delete(name: str, repo: str = ".") -> str:
    """Delete a local tag.

    Args:
        name: Tag name.
        repo: Repository path.
    """
    return _run_git(["tag", "-d", name], repo)


@tool
def git_push_tags(remote: str = "origin", repo: str = ".") -> str:
    """Push all tags to a remote.

    Args:
        remote: Remote name.
        repo: Repository path.
    """
    return _run_git(["push", remote, "--tags"], repo)


# --------------------------------------------------------------------------- #
# Remotes / network (outward-facing)
# --------------------------------------------------------------------------- #
@tool
def git_remote_list(repo: str = ".") -> str:
    """List configured remotes with URLs.

    Args:
        repo: Repository path.
    """
    return _run_git(["remote", "-v"], repo)


@tool
def git_remote_add(name: str, url: str, repo: str = ".") -> str:
    """Add a remote.

    Args:
        name: Remote name, e.g. 'origin'.
        url: Remote URL.
        repo: Repository path.
    """
    return _run_git(["remote", "add", name, url], repo) or f"Remote {name} added."


@tool
def git_fetch(remote: str = "origin", repo: str = ".") -> str:
    """Fetch from a remote.

    Args:
        remote: Remote name.
        repo: Repository path.
    """
    return _run_git(["fetch", remote], repo)


@tool
def git_pull(remote: str = "origin", branch: str = "", repo: str = ".") -> str:
    """Pull from a remote.

    Args:
        remote: Remote name.
        branch: Branch to pull (empty = current tracking branch).
        repo: Repository path.
    """
    args = ["pull", remote] + ([branch] if branch else [])
    return _run_git(args, repo)


@tool
def git_push(
    remote: str = "origin", branch: str = "", set_upstream: bool = False, repo: str = "."
) -> str:
    """Push to a remote.

    Args:
        remote: Remote name.
        branch: Branch to push (empty = current branch).
        set_upstream: Set upstream tracking (-u).
        repo: Repository path.
    """
    args = ["push"] + (["-u"] if set_upstream else []) + [remote]
    if branch:
        args += [branch]
    return _run_git(args, repo)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
@tool
def git_config_get(key: str, repo: str = ".") -> str:
    """Get a git config value.

    Args:
        key: Config key, e.g. 'user.email'.
        repo: Repository path.
    """
    return _run_git(["config", "--get", key], repo)


@tool
def git_config_set(key: str, value: str, repo: str = ".") -> str:
    """Set a local git config value.

    Args:
        key: Config key, e.g. 'user.email'.
        value: Value to set.
        repo: Repository path.
    """
    return _run_git(["config", key, value], repo) or f"Set {key}."


# --------------------------------------------------------------------------- #
# Hooks
# --------------------------------------------------------------------------- #
def _hooks_dir(repo):
    rp = resolve_safe_path(repo)
    # Respect a custom core.hooksPath if set, else default .git/hooks.
    r = subprocess.run(
        ["git", "-C", rp, "rev-parse", "--git-path", "hooks"],
        capture_output=True,
        text=True,
        env=_GIT_ENV,
    )
    rel = r.stdout.strip() or ".git/hooks"
    return os.path.join(rp, rel) if not os.path.isabs(rel) else rel


@tool
def git_list_hooks(repo: str = ".") -> str:
    """List installed git hooks (excludes .sample templates).

    Args:
        repo: Repository path.
    """
    hd = _hooks_dir(repo)
    if not os.path.isdir(hd):
        return "(no hooks directory)"
    hooks = [f for f in sorted(os.listdir(hd)) if not f.endswith(".sample")]
    return "\n".join(hooks) if hooks else "(no active hooks)"


@tool
def git_show_hook(name: str, repo: str = ".") -> str:
    """Show the contents of a git hook.

    Args:
        name: Hook name, e.g. 'pre-commit'.
        repo: Repository path.
    """
    path = os.path.join(_hooks_dir(repo), name)
    if not os.path.isfile(path):
        return f"Hook '{name}' not found."
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


@tool
def git_install_hook(name: str, script: str, repo: str = ".") -> str:
    """Install (write + make executable) a git hook, backing up any existing one.

    Args:
        name: Hook name, e.g. 'pre-commit'.
        script: Full hook script contents (include a shebang line).
        repo: Repository path.
    """
    hd = _hooks_dir(repo)
    os.makedirs(hd, exist_ok=True)
    path = resolve_safe_path(os.path.join(hd, name))
    backup_file(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(script if script.endswith("\n") else script + "\n")
    os.chmod(path, 0o755)
    return f"Installed hook '{name}' at {path}."


@tool
def git_remove_hook(name: str, repo: str = ".") -> str:
    """Remove a git hook (renames it to <name>._backup for safety, does not delete).

    Args:
        name: Hook name.
        repo: Repository path.
    """
    path = os.path.join(_hooks_dir(repo), name)
    if not os.path.isfile(path):
        return f"Hook '{name}' not found."
    backup_file(path)
    os.remove(path)
    return f"Removed hook '{name}' (backup kept)."


# --------------------------------------------------------------------------- #
# GitHub releases (via gh CLI)
# --------------------------------------------------------------------------- #
@tool
def gh_release_create(tag: str, title: str = "", notes: str = "", repo: str = ".") -> str:
    """Create a GitHub release for a tag (requires 'gh' authenticated + a remote).

    Args:
        tag: Tag name for the release, e.g. 'v1.0.0'.
        title: Release title (empty = tag name).
        notes: Release notes body.
        repo: Repository path.
    """
    args = ["release", "create", tag]
    if title:
        args += ["--title", title]
    args += ["--notes", notes]
    return _run_gh(args, repo)


@tool
def gh_release_list(repo: str = ".") -> str:
    """List GitHub releases (requires 'gh').

    Args:
        repo: Repository path.
    """
    return _run_gh(["release", "list"], repo)


@tool
def gh_release_view(tag: str, repo: str = ".") -> str:
    """View a GitHub release (requires 'gh').

    Args:
        tag: Release tag name.
        repo: Repository path.
    """
    return _run_gh(["release", "view", tag], repo)
