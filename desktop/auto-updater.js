/**
 * Git-based Auto-Updater & Environment Setup
 *
 * On every app launch:
 *   1. Check for git updates (fetch + compare HEAD vs origin/main)
 *   2. Pull if behind (git pull origin main)
 *   3. Ensure Python venv exists with correct deps
 *   4. Ensure frontend is built (npm install + npm run build if needed)
 *
 * Reports progress via callback so splash screen can show status.
 */
const { execFile, execFileSync, spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const crypto = require("crypto");
const log = require("electron-log");

const REPO_ROOT = path.join(__dirname, "..");
const BACKEND_DIR = path.join(REPO_ROOT, "backend");
const FRONTEND_DIR = path.join(REPO_ROOT, "frontend-v2");

// ── Helpers ──────────────────────────────────────────────────────────────────

function exec(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const proc = execFile(cmd, args, {
      cwd: REPO_ROOT,
      timeout: opts.timeout || 120_000,
      maxBuffer: 10 * 1024 * 1024,
      ...opts,
    }, (err, stdout, stderr) => {
      if (err) {
        err.stdout = stdout;
        err.stderr = stderr;
        reject(err);
      } else {
        resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
      }
    });
  });
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const spawnOpts = {
      cwd: opts.cwd || REPO_ROOT,
      stdio: ["ignore", "pipe", "pipe"],
    };
    if (opts.env) spawnOpts.env = opts.env;
    const proc = spawn(cmd, args, spawnOpts);
    const timeout = opts.timeout || 300_000;
    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      reject(new Error(`${cmd} timed out after ${timeout / 1000}s`));
    }, timeout);
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => { stdout += d.toString(); });
    proc.stderr.on("data", (d) => { stderr += d.toString(); });
    proc.on("error", (err) => { clearTimeout(timer); reject(err); });
    proc.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0 && !opts.allowFail) {
        const err = new Error(`${cmd} exited with code ${code}`);
        err.stdout = stdout;
        err.stderr = stderr;
        reject(err);
      } else {
        resolve({ stdout: stdout.trim(), stderr: stderr.trim(), code });
      }
    });
  });
}

function fileHash(filePath) {
  try {
    const content = fs.readFileSync(filePath);
    return crypto.createHash("sha256").update(content).digest("hex").slice(0, 16);
  } catch {
    return null;
  }
}

// ── Git Operations ──────────────────────────────────────────────────────────

async function isGitRepo() {
  try {
    await exec("git", ["rev-parse", "--git-dir"], { cwd: REPO_ROOT });
    return true;
  } catch {
    return false;
  }
}

async function getCurrentBranch() {
  try {
    const { stdout } = await exec("git", ["branch", "--show-current"], { cwd: REPO_ROOT });
    return stdout || "main";
  } catch {
    return "main";
  }
}

async function checkForUpdates(onStatus) {
  onStatus("Checking for updates...");

  if (!(await isGitRepo())) {
    log.warn("Not a git repository — skipping update check");
    return { updated: false, reason: "not-a-git-repo" };
  }

  const branch = await getCurrentBranch();
  log.info(`Current branch: ${branch}`);

  // Fetch with retry
  let fetched = false;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      onStatus(`Fetching updates (attempt ${attempt})...`);
      await exec("git", ["fetch", "origin", branch], { cwd: REPO_ROOT, timeout: 30_000 });
      fetched = true;
      break;
    } catch (err) {
      log.warn(`Git fetch attempt ${attempt} failed: ${err.message}`);
      if (attempt < 3) {
        await new Promise((r) => setTimeout(r, 2000 * attempt));
      }
    }
  }

  if (!fetched) {
    log.warn("Could not reach remote — running with local version");
    onStatus("Offline — using local version");
    return { updated: false, reason: "fetch-failed" };
  }

  // Compare local vs remote
  try {
    const { stdout: localHead } = await exec("git", ["rev-parse", "HEAD"], { cwd: REPO_ROOT });
    const { stdout: remoteHead } = await exec("git", ["rev-parse", `origin/${branch}`], { cwd: REPO_ROOT });

    if (localHead === remoteHead) {
      log.info("Already up to date");
      onStatus("Up to date");
      return { updated: false, reason: "up-to-date" };
    }

    // Check what files changed
    const { stdout: diffFiles } = await exec(
      "git", ["diff", "--name-only", "HEAD", `origin/${branch}`],
      { cwd: REPO_ROOT }
    );
    const changedFiles = diffFiles.split("\n").filter(Boolean);
    log.info(`${changedFiles.length} files changed on remote`);

    // Pull
    onStatus("Downloading updates...");
    await exec("git", ["pull", "origin", branch, "--ff-only"], { cwd: REPO_ROOT, timeout: 60_000 });
    log.info("Git pull successful");

    // Determine what needs rebuilding
    const backendDepsChanged = changedFiles.some(
      (f) => f === "backend/requirements.txt" || f.startsWith("backend/app/")
    );
    const frontendDepsChanged = changedFiles.some(
      (f) => f.startsWith("frontend-v2/package") || f.startsWith("frontend-v2/src/")
    );

    return {
      updated: true,
      changedFiles,
      backendDepsChanged,
      frontendDepsChanged,
    };
  } catch (err) {
    log.error("Update check failed:", err.message);
    onStatus("Update check failed — continuing with local version");
    return { updated: false, reason: "compare-failed", error: err.message };
  }
}

// ── Python Venv Management ──────────────────────────────────────────────────

function getPythonCommand() {
  // Try multiple Python commands
  const candidates = process.platform === "win32"
    ? ["python", "python3", "py -3"]
    : ["python3", "python"];

  for (const cmd of candidates) {
    try {
      const parts = cmd.split(" ");
      const result = execFileSync(parts[0], [...parts.slice(1), "--version"], {
        encoding: "utf8",
        timeout: 10_000,
      });
      const version = result.trim();
      const match = version.match(/Python (\d+)\.(\d+)/);
      if (match && (parseInt(match[1]) > 3 || (parseInt(match[1]) === 3 && parseInt(match[2]) >= 10))) {
        log.info(`Found ${version} via '${cmd}'`);
        return parts;
      }
    } catch {
      // Try next
    }
  }
  return null;
}

function getVenvPython() {
  const venvDir = path.join(BACKEND_DIR, "venv");
  if (process.platform === "win32") {
    return path.join(venvDir, "Scripts", "python.exe");
  }
  return path.join(venvDir, "bin", "python");
}

function getVenvPip() {
  const venvDir = path.join(BACKEND_DIR, "venv");
  if (process.platform === "win32") {
    return path.join(venvDir, "Scripts", "pip.exe");
  }
  return path.join(venvDir, "bin", "pip");
}

function venvExists() {
  return fs.existsSync(getVenvPython());
}

// Hash file to detect changes
const HASH_FILE = path.join(BACKEND_DIR, ".deps-hash");

function depsChanged() {
  const currentHash = fileHash(path.join(BACKEND_DIR, "requirements.txt"));
  if (!currentHash) return true;
  try {
    const savedHash = fs.readFileSync(HASH_FILE, "utf8").trim();
    return savedHash !== currentHash;
  } catch {
    return true;
  }
}

function saveDepsHash() {
  const hash = fileHash(path.join(BACKEND_DIR, "requirements.txt"));
  if (hash) fs.writeFileSync(HASH_FILE, hash, "utf8");
}

async function ensurePythonEnv(onStatus) {
  onStatus("Checking Python environment...");

  const pythonCmd = getPythonCommand();
  if (!pythonCmd) {
    throw new Error(
      "Python 3.10+ not found.\n\n" +
      "Install Python from https://www.python.org/downloads/\n" +
      "Make sure to check 'Add Python to PATH' during installation."
    );
  }

  // Create venv if missing
  if (!venvExists()) {
    onStatus("Creating Python environment (first run)...");
    log.info("Creating Python venv...");
    await run(pythonCmd[0], [...pythonCmd.slice(1), "-m", "venv", "venv"], {
      cwd: BACKEND_DIR,
      timeout: 120_000,
    });
    log.info("Python venv created");
  }

  // Install/update dependencies if changed
  if (depsChanged()) {
    onStatus("Installing Python dependencies...");
    log.info("Installing pip dependencies (requirements.txt changed)...");
    const pip = getVenvPip();
    await run(pip, ["install", "--upgrade", "pip"], {
      cwd: BACKEND_DIR,
      timeout: 120_000,
      allowFail: true,
    });
    await run(pip, ["install", "-r", "requirements.txt"], {
      cwd: BACKEND_DIR,
      timeout: 600_000, // 10 min for full install
    });
    saveDepsHash();
    log.info("Python dependencies installed");
  } else {
    log.info("Python dependencies up to date");
  }

  onStatus("Python environment ready");
}

// ── Frontend Build ──────────────────────────────────────────────────────────

function getNpmCommand() {
  return process.platform === "win32" ? "npm.cmd" : "npm";
}

const FRONTEND_HASH_FILE = path.join(FRONTEND_DIR, ".deps-hash");

function frontendDepsChanged() {
  const lockHash = fileHash(path.join(FRONTEND_DIR, "package-lock.json"))
    || fileHash(path.join(FRONTEND_DIR, "package.json"));
  if (!lockHash) return true;
  try {
    const savedHash = fs.readFileSync(FRONTEND_HASH_FILE, "utf8").trim();
    return savedHash !== lockHash;
  } catch {
    return true;
  }
}

function saveFrontendDepsHash() {
  const hash = fileHash(path.join(FRONTEND_DIR, "package-lock.json"))
    || fileHash(path.join(FRONTEND_DIR, "package.json"));
  if (hash) fs.writeFileSync(FRONTEND_HASH_FILE, hash, "utf8");
}

function frontendDistExists() {
  return fs.existsSync(path.join(FRONTEND_DIR, "dist", "index.html"));
}

// Track whether frontend source changed since last build
const FRONTEND_BUILD_HASH = path.join(FRONTEND_DIR, ".build-hash");

function frontendSourceChanged() {
  // Check if dist exists at all
  if (!frontendDistExists()) return true;

  // Compare package.json + a quick check of src/ modification time
  const pkgHash = fileHash(path.join(FRONTEND_DIR, "package.json"));
  const viteHash = fileHash(path.join(FRONTEND_DIR, "vite.config.js"));
  const combinedHash = `${pkgHash}-${viteHash}`;

  try {
    const savedHash = fs.readFileSync(FRONTEND_BUILD_HASH, "utf8").trim();
    return savedHash !== combinedHash;
  } catch {
    return true;
  }
}

function saveFrontendBuildHash() {
  const pkgHash = fileHash(path.join(FRONTEND_DIR, "package.json"));
  const viteHash = fileHash(path.join(FRONTEND_DIR, "vite.config.js"));
  fs.writeFileSync(FRONTEND_BUILD_HASH, `${pkgHash}-${viteHash}`, "utf8");
}

async function ensureFrontendBuild(onStatus, forceRebuild = false) {
  const npm = getNpmCommand();
  const nodeModulesExist = fs.existsSync(path.join(FRONTEND_DIR, "node_modules"));

  // Install npm deps if needed
  if (!nodeModulesExist || frontendDepsChanged()) {
    onStatus("Installing frontend dependencies...");
    log.info("Running npm install in frontend-v2...");
    await run(npm, ["install"], {
      cwd: FRONTEND_DIR,
      timeout: 300_000, // 5 min
    });
    saveFrontendDepsHash();
    log.info("Frontend npm install complete");
  }

  // Build if needed
  if (forceRebuild || !frontendDistExists() || frontendSourceChanged()) {
    onStatus("Building frontend...");
    log.info("Running npm run build in frontend-v2...");

    // Set API URL for Electron builds — frontend loads from file:// so needs absolute URL
    const backendPort = require("./device-config").getBackendPort();
    const buildEnv = {
      ...process.env,
      VITE_API_URL: `http://127.0.0.1:${backendPort}`,
      VITE_WS_URL: `ws://127.0.0.1:${backendPort}/ws`,
    };

    await run(npm, ["run", "build"], {
      cwd: FRONTEND_DIR,
      timeout: 300_000,
      env: buildEnv,
    });
    saveFrontendBuildHash();
    log.info("Frontend build complete");
  } else {
    log.info("Frontend build up to date");
  }

  onStatus("Frontend ready");
}

// ── Full Startup Sequence ───────────────────────────────────────────────────

async function runStartupSequence(onStatus) {
  const results = {
    updateCheck: null,
    pythonSetup: false,
    frontendBuild: false,
    errors: [],
  };

  // Step 1: Check for git updates
  try {
    results.updateCheck = await checkForUpdates(onStatus);
  } catch (err) {
    log.error("Update check error:", err.message);
    results.errors.push(`Update check: ${err.message}`);
  }

  // Step 2: Ensure Python environment
  try {
    await ensurePythonEnv(onStatus);
    results.pythonSetup = true;
  } catch (err) {
    log.error("Python setup error:", err.message);
    results.errors.push(`Python setup: ${err.message}`);
    throw err; // Python is required — can't continue without it
  }

  // Step 3: Ensure frontend is built
  try {
    const forceRebuild = results.updateCheck?.frontendDepsChanged || false;
    await ensureFrontendBuild(onStatus, forceRebuild);
    results.frontendBuild = true;
  } catch (err) {
    log.error("Frontend build error:", err.message);
    results.errors.push(`Frontend build: ${err.message}`);
    // Not fatal — backend can still run, we just won't have a UI
  }

  return results;
}

// ── Exports ─────────────────────────────────────────────────────────────────

module.exports = {
  runStartupSequence,
  checkForUpdates,
  ensurePythonEnv,
  ensureFrontendBuild,
  getVenvPython,
  venvExists,
  frontendDistExists,
  REPO_ROOT,
  BACKEND_DIR,
  FRONTEND_DIR,
};
