# Manual private GitHub backup

## Before the first push

The agent never pushes, creates a remote repository or changes GitHub authentication.

Proposed destination: **`parand1khalili/llm-gnn-sara`**. It has NOT been created or verified by the agent. The repository URL below is conditional, not evidence that it exists.

The user must first:

1. Sign into GitHub as `parand1khalili` using their own normal authentication.
2. Create a repository named `llm-gnn-sara` under that owner, explicitly select **Private**, and leave initialization with README, `.gitignore` and license unchecked so the remote is empty.
3. Open the resulting repository page and verify the exact owner/name and **Private** visibility. Do not run the push commands if either differs.
4. Review the latest local commit and tracked file list. Keep datasets, weights, raw responses, archives and private authentication files excluded. Any licensing/redistribution questions about recovered upstream code must be reviewed before broader sharing.
5. Complete any Git credential prompt yourself. Never paste credentials or access tokens into chat, a script, a repository URL or a report.

## Exact first-push commands (user runs manually)

Run this block only after the above private, empty destination has been created and visually verified. It never force-pushes, changes authentication or points at upstream. It uses the known bundled Git because `git` was not on PATH here.

```powershell
$repo = 'C:\Users\Admin\Documents\ChatGPT\llm-gnn'
$g = 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
$url = 'https://github.com/parand1khalili/llm-gnn-sara.git'

Set-Location -LiteralPath $repo
$dirty = & $g -c "safe.directory=$repo" -C $repo status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect the local repository.' }
if ($dirty) { throw 'Working tree is not clean. Review and commit before pushing.' }
& $g -c "safe.directory=$repo" -C $repo log -1 --oneline
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect the commit.' }

$existing = & $g -c "safe.directory=$repo" -C $repo ls-remote $url
if ($LASTEXITCODE -ne 0) { throw 'Remote is unavailable or authentication failed. Stop.' }
if ($existing) { throw 'First-push destination is not empty. Stop; do not force-push.' }

& $g -c "safe.directory=$repo" -C $repo push $url 'main:main'
if ($LASTEXITCODE -ne 0) { throw 'Push failed. Backup remains PUSH_PENDING.' }

$localSha = & $g -c "safe.directory=$repo" -C $repo rev-parse main
if ($LASTEXITCODE -ne 0) { throw 'Cannot read local SHA.' }
$remoteLine = & $g -c "safe.directory=$repo" -C $repo ls-remote $url 'refs/heads/main'
if ($LASTEXITCODE -ne 0 -or -not $remoteLine) { throw 'Remote verification failed.' }
$remoteSha = ($remoteLine -split '\s+')[0]
if ($localSha -ne $remoteSha) { throw 'Remote SHA differs. Backup is not verified.' }
Write-Output "Verified remote main SHA: $remoteSha"
```

This does not add or change any local remote configuration. `ls-remote` alone cannot verify visibility; the Private/owner check in the GitHub UI is mandatory before executing the block. Return its verification result to this chat; the agent will independently read the remote when access is available before declaring the GitHub backup complete.

## Later daily pushes

After the destination is established, review the clean local commits, run the same explicit `push $url 'main:main'` manually, and repeat local/remote SHA comparison. Do not use the first-push empty-remote check again. On a non-fast-forward rejection, stop and review; never force-push. Until remote verification succeeds, local commits remain `PUSH_PENDING`.
