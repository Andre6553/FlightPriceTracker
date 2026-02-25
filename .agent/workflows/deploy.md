---
description: Deploy the latest changes to GitHub
---

This workflow stages all your changes, commits them, and pushes them to your GitHub repository.

// turbo-all

1. Stage all modified and new files:
`git add .`

2. Commit the changes:
`git commit -m "Auto-deploy: Update project files"`

3. Push the changes to your remote repository:
`git push origin main`
