---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git diff:*), Bash(git commit:*), Bash(git push:*)
description: Git commit and push with basic security checks
---


## Security Checks
1. **Check git diff for secrets**:
```bash
   git diff HEAD | grep -iE "(api[_-]?key|secret|password|token|private[_-]?key|\.env)"
```

2. **Check for files that should be gitignored**:
```bash
   git status --porcelain | grep -E "\.(env|log)$|node_modules/|\.DS_Store"
```

3. **Quick scan of staged files**:
```bash
   git diff --cached | grep -E "(BEGIN (RSA )?PRIVATE KEY|api[_-]?key.*=|password.*=)"
```

## Rules
- ❌ **STOP** if any secrets/keys found
- ❌ **STOP** if .env files or node_modules being committed  
- ✅ **PROCEED** if all clear

## Commit Steps
1. Run `git status` to see all changes
2. Run `git diff` to review the changes  
3. Analyze changes and determine conventional commit type:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `style:` for formatting changes
   - `refactor:` for code refactoring
   - `test:` for test additions/changes
   - `chore:` for maintenance tasks
4. Stage all changes with `git add -A`
5. Create a conventional commit with descriptive message
6. Push to current branch with `git push`

Remember: Follow Conventional Commits specification.