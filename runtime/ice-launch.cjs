#!/usr/bin/env node

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const ROOT = process.cwd();

const REPOS = {
  strap: ROOT,
  engine: path.resolve(ROOT, "../ice-engine"),
  protocols: path.resolve(ROOT, "../ice-protocols"),
  gui: path.resolve(ROOT, "../ice-studio-gui"),
};

function fatal(msg) {
  console.error("[ICE-STRAP][FATAL]", msg);
  process.exit(1);
}

function spawnProc(label, cmd, args, opts = {}) {
  console.log(`[ICE-STRAP] starting ${label}`);
  return spawn(cmd, args, {
    stdio: "inherit",
    cwd: opts.cwd || ROOT,
    env: opts.env || process.env,
  });
}

/* sanity check */
for (const [k, p] of Object.entries(REPOS)) {
  if (!fs.existsSync(p)) {
    fatal(`missing repo: ${k} (${p})`);
  }
}

/* PYTHONPATH CANONICO */
const PYTHONPATH = [
  REPOS.strap,
  REPOS.engine,
  REPOS.protocols,
].join(":");

/* 1. PREBOOT */
spawnProc(
  "preboot",
  "python",
  ["-m", "runtime.preboot.main"],
  {
    cwd: REPOS.strap,
    env: {
      ...process.env,
      PYTHONPATH,
      ICE_PHASE: "preboot",
    },
  }
);

/* 2. ELECTRON GUI */
spawnProc(
  "gui",
  "npm",
  ["start"],
  {
    cwd: path.join(REPOS.gui, "electron"),
  }
);
