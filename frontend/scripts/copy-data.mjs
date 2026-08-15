// Prebuild step for the static (public) deployment: copies the committed
// reference snapshot + omissions log into public/data/ so the built site
// serves them as plain files — no API, no key, nothing anyone can spend.
import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";

const repoData = join(import.meta.dirname, "..", "..", "data");
const publicData = join(import.meta.dirname, "..", "public", "data");

mkdirSync(publicData, { recursive: true });

const snapshots = readdirSync(repoData)
  .filter((f) => f.startsWith("snapshot_") && f.endsWith(".json"))
  .sort();

if (snapshots.length === 0) {
  console.warn("copy-data: no snapshot_*.json in data/ — building with an empty dashboard");
} else {
  const latest = snapshots[snapshots.length - 1];
  copyFileSync(join(repoData, latest), join(publicData, "snapshot.json"));
  console.log(`copy-data: ${latest} -> public/data/snapshot.json`);
}

const omissions = join(repoData, "omissions.json");
if (existsSync(omissions)) {
  copyFileSync(omissions, join(publicData, "omissions.json"));
  console.log("copy-data: omissions.json -> public/data/omissions.json");
}
