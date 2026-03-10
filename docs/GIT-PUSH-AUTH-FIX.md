# Fixing GitHub 403 on `git push`

A 403 on push means GitHub is rejecting your credentials. GitHub no longer accepts account passwords for HTTPS—use a **Personal Access Token (PAT)** or **SSH** instead.

---

## Option A: HTTPS with a Personal Access Token

### 1. Create a token

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. **Generate new token (classic)**
3. Name it (e.g. `elite-trading-system`), set expiration, enable the **`repo`** scope
4. Copy the token immediately (it won't be shown again)

### 2. Use the token

When Git prompts for a password, paste the **token** (not your GitHub password).

**Store it permanently (Windows Credential Manager):**

```powershell
cd C:\Users\Espen\Dev\elite-trading-system
git config credential.helper manager
```

Next `git push` will prompt once—use your GitHub username and the token as password. Windows remembers it.

**Or embed in remote URL (quick but less secure):**

```powershell
git remote set-url origin https://Espenator@github.com/Espenator/elite-trading-system.git
# git push will prompt for password → paste token
```

---

## Option B: SSH

### 1. Check for an existing key

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
# or
Get-Content $env:USERPROFILE\.ssh\id_rsa.pub
```

### 2. Generate a key (if none exists)

```powershell
ssh-keygen -t ed25519 -C "your_email@example.com" -f $env:USERPROFILE\.ssh\id_ed25519 -N '""'
```

Add the public key: GitHub → **Settings** → **SSH and GPG keys** → **New SSH key** → paste `id_ed25519.pub`.

### 3. Switch remote to SSH and push

```powershell
cd C:\Users\Espen\Dev\elite-trading-system
git remote set-url origin git@github.com:Espenator/elite-trading-system.git
git push origin main
```

---

## Quick Checklist

| Check | Detail |
|-------|--------|
| HTTPS password | Must be a **PAT**, not your login password |
| Token scope | Must include **`repo`** |
| Account match | Token/SSH key must belong to **Espenator** (owner or collaborator) |

After fixing auth, verify with:

```powershell
git push origin main
```
