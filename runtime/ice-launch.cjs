#!/usr/bin/env node

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const ROOT = process.cwd();
const REPOS = {
  engine: path.resolve(ROOT, "../ice-engine"),
  gui: path.resolve(ROOT, "../ice-studio-gui")
};

function fatal(msg) {
  console.error("[ICE-STRAP][FATAL]", msg);
  process.exit(1);
}

function spawnProc(label, cmd, args, opts = {}) {
  console.log(`[ICE-STRAP] starting ${label}`);
  return spawn(cmd, args, {
    stdio: "inherit",
    env: process.env,
    cwd: opts.cwd || ROOT
  });
}

/* sanity */
for (const [k, p] of Object.entries(REPOS)) {
  if (!fs.existsSync(p)) {
    fatal(`missing repo: ${k} (${p})`);
  }
}

spawnProc(
  "preboot",
  "python",
  ["-m", "engine.preboot.main"],
  {
    cwd: REPOS.engine,
    env: {
      ...process.env,
      PYTHONPATH: REPOS.engine,
      ICE_PHASE: "preboot"
    }
  }
);




/* 2. ELECTRON GUI */
spawnProc(
  "gui",
  "npm",
  ["start"],
  { cwd: path.join(REPOS.gui, "electron") }
);
