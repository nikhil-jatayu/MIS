import { execFileSync } from "node:child_process";
import path from "node:path";

export default function globalTeardown() {
  const backendDir = path.resolve(process.cwd(), "..", "backend");
  const python =
    process.platform === "win32"
      ? path.join(backendDir, ".venv", "Scripts", "python.exe")
      : path.join(backendDir, ".venv", "bin", "python");

  execFileSync(
    python,
    [path.join(backendDir, "tests", "e2e_fixture.py"), "cleanup"],
    { cwd: backendDir, stdio: "inherit" },
  );
}
