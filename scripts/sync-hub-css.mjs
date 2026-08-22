import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
mkdirSync(join(root, "sites/nika-crm-hub/css"), { recursive: true });
mkdirSync(join(root, "sites/nika-crm-hub/js"), { recursive: true });
copyFileSync(
  join(root, "static/css/nika.build.css"),
  join(root, "sites/nika-crm-hub/css/nika.build.css"),
);
copyFileSync(
  join(root, "static/js/nika-ui.js"),
  join(root, "sites/nika-crm-hub/js/nika-ui.js"),
);
