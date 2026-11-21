"""Run the skill's approval dependency and patch commands with the real CLI."""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[1] / "plugins/flow-atelier/skills/flow-atelier/SKILL.md"
PATCH = """diff --git a/release.txt b/release.txt
new file mode 100644
--- /dev/null
+++ b/release.txt
@@ -0,0 +1 @@
+approved release
"""


class ApprovalExampleTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / "release.patch").write_text(PATCH)
        self.target = self.root / "release.txt"

        skill = SKILL.read_text()
        blocks = re.findall(r"```yaml\n(.*?)```", skill, re.S)
        pipeline = next(block for block in blocks if block.startswith("name: deploy_pipeline"))
        tasks = {}
        for entry in yaml.safe_load(pipeline)["tasks"]:
            tasks.update(entry)
        section = skill.split("### Approving an exact patch\n")[1].split("\n### ")[0]
        self.preview, self.apply = re.findall(r"```bash\n(.*?)```", section, re.S)
        prompt = re.search(r"`(Review git cat-file -p .*?)`", section).group(1)
        self.approve = dict(tasks["approve"], depends_on=["preview"], task=prompt)
        self.dependency = tasks["deploy"]["depends_on"]

    def write_conduit(self, before="", after=""):
        folder = self.root / ".atelier/conduits/demo"
        folder.mkdir(parents=True)
        tasks = [
            {"preview": {"description": "Snapshot", "tool": "tool:bash", "task": self.preview}},
            {"approve": self.approve},
            {"deploy": {"description": "Apply locally", "tool": "tool:bash",
                        "depends_on": self.dependency, "task": before + self.apply + after}},
        ]
        (folder / "conduit.yaml").write_text(yaml.safe_dump(
            {"name": "demo", "description": "Local approval example", "tasks": tasks}
        ))

    def run_flow(self, *args, answer="", success=True):
        env = {k: v for k, v in os.environ.items() if not k.startswith("ATELIER_")}
        env.update(ATELIER_GLOBAL_ATELIER_DIR=str(self.root / "global"), ATELIER_NO_UPDATE_CHECK="1")
        result = subprocess.run(["atelier", "run", *args], cwd=self.root, env=env,
                                input=answer, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_only_yes_deploys(self):
        self.write_conduit()
        for answer in ("no", "", "yesterday", "confirm: 'yes'"):
            with self.subTest(answer=answer):
                self.run_flow("demo", answer=answer + "\n")
                self.assertFalse(self.target.exists())
        output = self.run_flow("demo", answer="yes\n")
        digest = subprocess.check_output(
            ["git", "hash-object", "--no-filters", "release.patch"], cwd=self.root, text=True
        ).strip()
        self.assertIn(f"git cat-file -p {digest}", output)
        self.assertEqual(self.target.read_text(), "approved release\n")

    def test_changed_patch_requires_new_approval(self):
        self.write_conduit(before="echo changed >> release.patch\n")
        output = self.run_flow("demo", answer="yes\n", success=False)
        self.assertIn("Patch changed since approval", output)
        self.assertFalse(self.target.exists())

    def test_resume_after_apply_preserves_the_deployed_file(self):
        self.write_conduit(after="test -f acknowledged\n")
        self.run_flow("demo", answer="yes\n", success=False)
        self.assertEqual(self.target.read_text(), "approved release\n")
        deployed = self.target.stat()
        (self.root / "acknowledged").touch()
        self.run_flow("--resume", "latest")
        self.assertEqual(self.target.stat().st_mtime_ns, deployed.st_mtime_ns)
        self.assertEqual(self.target.read_text(), "approved release\n")
