import { execFileSync } from "node:child_process";
import path from "node:path";

function runFixture(action: "ensure" | "cleanup") {
  const backendDir = path.resolve(process.cwd(), "..", "backend");
  const python =
    process.platform === "win32"
      ? path.join(backendDir, ".venv", "Scripts", "python.exe")
      : path.join(backendDir, ".venv", "bin", "python");

  execFileSync(
    python,
    [path.join(backendDir, "tests", "e2e_fixture.py"), action],
    { cwd: backendDir, stdio: "inherit" },
  );
}

export default function globalSetup() {
  runFixture("ensure");
}
