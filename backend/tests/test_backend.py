import asyncio
import os
import tempfile
import unittest

from app.main import extract_resume_text, normalize_roadmap_payload


class BackendBehaviorTests(unittest.TestCase):
    def test_extract_resume_text_supports_plain_text_files(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("Jane Doe\nSoftware Engineer\nBuilt a React and FastAPI app")
            temp_path = handle.name

        try:
            text = asyncio.run(extract_resume_text(temp_path, "resume.txt"))
            self.assertIn("Jane Doe", text)
            self.assertIn("React", text)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_normalize_roadmap_payload_builds_tree_nodes(self) -> None:
        payload = {
            "title": "Launch plan",
            "overview": "Ship the product",
            "total_weeks": 8,
            "nodes": [
                {
                    "id": 1,
                    "name": "Planning",
                    "tasks": ["Scope", "Budget"],
                    "children": [
                        {"id": 2, "name": "Design", "tasks": ["Wireframes"]}
                    ],
                }
            ],
        }

        normalized = normalize_roadmap_payload(payload)
        self.assertEqual(normalized["title"], "Launch plan")
        self.assertEqual(normalized["nodes"][0]["title"], "Planning")
        self.assertEqual(normalized["nodes"][0]["details"], "Scope; Budget")
        self.assertEqual(normalized["nodes"][0]["children"][0]["title"], "Design")


if __name__ == "__main__":
    unittest.main()
