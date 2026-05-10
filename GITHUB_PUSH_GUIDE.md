# GitHub Push Instructions

Push your project to: https://github.com/rajishnse-alt/trade_setup2026/

---

## 🚀 Quick Push (Copy & Paste)

```bash
cd ~/Documents/Trading/my_trade_setup

git init
git config user.name "Your Name"
git config user.email "rajish.g.nair@gmail.com"

git remote add origin https://github.com/rajishnse-alt/trade_setup2026.git

git add .
git commit -m "Initial commit: PCR analysis tool for Nifty & Bank Nifty"

git branch -M main
git push -u origin main
```

---

## 📋 Step-by-Step Guide

### Step 1: Navigate to Project
```bash
cd ~/Documents/Trading/my_trade_setup
```

### Step 2: Initialize Git
```bash
git init
git config user.name "Your Name"
git config user.email "rajish.g.nair@gmail.com"
```

### Step 3: Add Remote
```bash
git remote add origin https://github.com/rajishnse-alt/trade_setup2026.git
```

### Step 4: Stage Files
```bash
git add .
```

Verify with:
```bash
git status
```

Should show:
```
On branch master

Initial commit

Changes to be committed:
  new file:   pcr_analysis.py
  new file:   requirements.txt
  new file:   README.md
  new file:   .gitignore
  new file:   .streamlit/config.toml
```

### Step 5: Create First Commit
```bash
git commit -m "Initial commit: PCR analysis tool for Nifty & Bank Nifty options trading"
```

### Step 6: Set Main Branch
```bash
git branch -M main
```

### Step 7: Push to GitHub
```bash
git push -u origin main
```

---

## 🔑 Authentication Methods

### Option 1: Personal Access Token (PAT) - Recommended
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `user`
4. Copy the token
5. When pushing, use:
   ```bash
   git push -u https://YOUR_TOKEN@github.com/rajishnse-alt/trade_setup2026.git main
   ```

### Option 2: SSH Key
1. Check if SSH key exists:
   ```bash
   cat ~/.ssh/id_rsa.pub
   ```
2. If not, create one:
   ```bash
   ssh-keygen -t rsa -b 4096 -C "rajish.g.nair@gmail.com"
   ```
3. Add to GitHub: https://github.com/settings/keys
4. Change remote:
   ```bash
   git remote remove origin
   git remote add origin git@github.com:rajishnse-alt/trade_setup2026.git
   ```
5. Push:
   ```bash
   git push -u origin main
   ```

### Option 3: GitHub CLI
1. Install GitHub CLI: https://cli.github.com
2. Authenticate:
   ```bash
   gh auth login
   ```
3. Push:
   ```bash
   git branch -M main
   git push -u origin main
   ```

---

## ✅ Verify Push Success

After pushing, verify at:
https://github.com/rajishnse-alt/trade_setup2026

Should see:
- ✅ `pcr_analysis.py`
- ✅ `requirements.txt`
- ✅ `README.md`
- ✅ `.gitignore`
- ✅ `.streamlit/config.toml`

---

## 🔒 Important: Security Check

Make sure `.gitignore` prevents these from being uploaded:
- ❌ `.streamlit/secrets.toml` (API keys!)
- ❌ `__pycache__/`
- ❌ `.venv/` or `venv/`
- ❌ `*.log` files

Check with:
```bash
git ls-files | grep -E "(secrets|__pycache__|\.log)"
```

Should return nothing!

---

## 🐛 Troubleshooting

### "Repository not found"
```bash
# Check remote URL
git remote -v

# Should show:
# origin  https://github.com/rajishnse-alt/trade_setup2026.git (fetch)
# origin  https://github.com/rajishnse-alt/trade_setup2026.git (push)
```

### "Permission denied (publickey)"
Use HTTPS with token instead of SSH:
```bash
git remote set-url origin https://YOUR_TOKEN@github.com/rajishnse-alt/trade_setup2026.git
```

### "fatal: refusing to merge unrelated histories"
```bash
git pull origin main --allow-unrelated-histories
git push origin main
```

### "fatal: You are not currently on a branch"
```bash
git checkout -b main
git push -u origin main
```

---

## 🔄 Future Updates

After initial push, updating is simple:

```bash
# Make changes
git add .
git commit -m "Feature: Add new functionality"
git push origin main
```

---

## 📊 Repository Settings

Once pushed, configure on GitHub:

1. **Settings** → **General**
   - Description: "PCR analysis tool for Nifty & Bank Nifty options"
   - Homepage: "https://github.com/rajishnse-alt/trade_setup2026"

2. **Settings** → **Collaborators** (if needed)
   - Add team members

3. **Settings** → **Webhooks** (optional)
   - For CI/CD integration

4. **README.md** will auto-display on repo main page

---

## 📚 Useful Git Commands

```bash
# Check status
git status

# View changes
git diff

# View commit history
git log --oneline

# Undo last commit (keep files)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Create new branch
git checkout -b feature/new-feature

# Switch branch
git checkout main

# Merge branch
git merge feature/new-feature
```

---

## 🎯 Next Steps After Push

1. **Verify** at: https://github.com/rajishnse-alt/trade_setup2026
2. **Deploy** to Streamlit Cloud (optional)
3. **Share** with team
4. **Track** changes with git

---

## ⚠️ Security Reminders

**NEVER commit:**
- `.streamlit/secrets.toml` (contains API keys!)
- Password files
- Private certificates
- Database credentials

**ALWAYS use:**
- `.gitignore` to exclude secrets
- Environment variables
- Secret management tools

---

**Ready? Run the quick push commands above!**
