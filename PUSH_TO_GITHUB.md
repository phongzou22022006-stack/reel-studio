# Push to GitHub

## Step 1: Create GitHub repo

Go to https://github.com/new and create a new repository:
- Name: `reel-studio`
- Description: Facebook Reels automation with templating & human-in-the-loop workflow
- Private or Public: your choice
- DO NOT initialize with README (we already have one)

## Step 2: Push code

```bash
cd /root/.openclaw/workspace/reel-studio

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/reel-studio.git

# Rename branch to main
git branch -M main

# Push
git push -u origin main
```

## Step 3: Verify

Open https://github.com/YOUR_USERNAME/reel-studio and check that all files are there.

---

**Repo is ready locally at:**
`/root/.openclaw/workspace/reel-studio`

**Files committed:**
- 21 Python files
- Config, README, LICENSE
- CLI + API + services
- Total: 24 files, ~4600 lines

**Next steps:**
1. Create GitHub repo
2. Push code
3. Copy `config.example.toml` to `config.toml` and configure
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `python cli.py --topic "test"`
