# Contributing to Daily Accomplishments

Thank you for your interest in contributing! This guide will help you work with git effectively in this repository.

## Git Workflow Guide

### 1. Initial Setup

Configure your git credentials:
```bash
git config user.name "Your GitHub Username"
git config user.email "your.email@example.com"
```

### 2. Making Changes

When working in Jupyter notebooks or remote environments:

**✅ DO:**
```bash
# Always use -m flag for commits
git commit -m "Clear, descriptive commit message"
```

**❌ DON'T:**
```bash
# Avoid using commit without -m flag
git commit
# This will try to open an editor which may not be available
```

### 3. Commit Message Guidelines

Write clear, concise commit messages:

- Use present tense: "Add feature" not "Added feature"
- Be descriptive: "Update dashboard.html: Integrate meeting time visualization"
- Keep first line under 72 characters
- Add detailed explanation in body if needed

**Good examples:**
```bash
git commit -m "Add hourly focus visualization to dashboard"
git commit -m "Fix: Correct category distribution calculation"
git commit -m "Update: Improve report generation performance"
```

**Poor examples:**
```bash
git commit -m "updates"
git commit -m "fix"
git commit -m "changes"
```

### 4. Working with Branches

Create a branch for new features:
```bash
git checkout -b feature/your-feature-name
git add .
git commit -m "Implement new feature"
git push -u origin feature/your-feature-name
```

### 5. Syncing with Remote

Before starting work:
```bash
git pull origin main
```

After committing changes:
```bash
git push origin your-branch-name
```

### 6. Common Git Commands

| Command | Purpose |
|---------|---------|
| `git status` | Check current changes |
| `git add <file>` | Stage specific file |
| `git add .` | Stage all changes |
| `git commit -m "message"` | Commit with message |
| `git push` | Push to remote |
| `git pull` | Pull from remote |
| `git log --oneline` | View commit history |
| `git diff` | See unstaged changes |

### 7. Troubleshooting

#### Editor Error

If you see:
```
error: there was a problem with the editor
```

**Solution:** Always use the `-m` flag:
```bash
git commit -m "Your commit message"
```

#### Configure Default Editor (Optional)

If you prefer using an editor:
```bash
git config --global core.editor "nano"
```

However, in Colab/Jupyter environments, using `-m` is recommended.

### 8. File Handling

**Files to commit:**
- Source code (`.ipynb`, `.py`, `.js`)
- Documentation (`.md`, `.txt`)
- Configuration files

**Files to ignore:**
- Temporary files
- Build artifacts
- Large generated files (unless needed)
- Personal configuration files

### 9. Using Git in Jupyter Notebooks

When running git commands in Jupyter cells, prefix with `!`:

```python
!git add dashboard.html
!git commit -m "Update dashboard visualization"
!git push
```

### 10. Best Practices

1. **Commit frequently** - Small, logical commits are better than large ones
2. **Pull before you push** - Avoid merge conflicts
3. **Write meaningful messages** - Help others understand your changes
4. **Test before committing** - Ensure your code works
5. **Use -m flag** - Avoid editor-related errors

## Questions?

If you encounter any issues or have questions about the git workflow, please open an issue or refer to the [README.md](README.md) for more information.
