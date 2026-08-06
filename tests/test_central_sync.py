import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import httpx


class CentralSyncApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="study-system-sync-")
        root = Path(cls.temp_dir.name)
        hermes_home = root / "hermes"
        os.environ["HERMES_HOME"] = str(hermes_home)
        os.environ["STUDY_DB_PATH"] = str(root / "study-system.sqlite3")
        sys.modules.pop("server", None)
        import server

        cls.server = server
        server.SESSIONS["token-alice"] = "alice"
        server.SESSIONS["token-bob"] = "bob"
        server.SESSIONS["token-pieye"] = "pieye"

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("HERMES_HOME", None)
        os.environ.pop("STUDY_DB_PATH", None)
        cls.temp_dir.cleanup()

    def run_async(self, coroutine):
        return asyncio.run(coroutine)

    def test_versioned_sync_isolation_and_migration(self):
        async def scenario():
            transport = httpx.ASGITransport(app=self.server.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                unauthenticated = await client.get("/api/data")
                self.assertEqual(unauthenticated.status_code, 401)

                client.cookies.set(self.server.SESSION_COOKIE, "token-alice")
                empty = await client.get("/api/data")
                self.assertEqual(empty.status_code, 200)
                self.assertIsNone(empty.json()["data"])
                self.assertEqual(empty.json()["revision"], 0)

                first = await client.put(
                    "/api/data",
                    json={
                        "base_revision": 0,
                        "data": {
                            "version": 2,
                            "xp": 10,
                            "items": [],
                            "habits": [],
                            "wishlist": [],
                            "logs": [],
                        },
                    },
                )
                self.assertEqual(first.status_code, 200)
                self.assertEqual(first.json()["revision"], 1)

                conflict = await client.put(
                    "/api/data",
                    json={"base_revision": 0, "data": {"version": 2, "xp": 999}},
                )
                self.assertEqual(conflict.status_code, 409)
                self.assertEqual(conflict.json()["current"]["revision"], 1)

                client.cookies.set(self.server.SESSION_COOKIE, "token-bob")
                isolated = await client.get("/api/data")
                self.assertEqual(isolated.status_code, 200)
                self.assertIsNone(isolated.json()["data"])

                client.cookies.set(self.server.SESSION_COOKIE, "token-alice")
                philosophy = await client.get("/api/philosophy/progress")
                self.assertEqual(philosophy.status_code, 200)
                self.assertEqual(philosophy.json()["revision"], 0)
                completed = await client.post(
                    "/api/philosophy/complete",
                    json={
                        "lesson_num": 1,
                        "question": "Q",
                        "user_summary": "S",
                        "topics_raised": [],
                        "depth_rating": 2,
                        "base_revision": 0,
                    },
                )
                self.assertEqual(completed.status_code, 200)
                self.assertEqual(completed.json()["revision"], 1)

                root = Path(self.temp_dir.name) / "hermes" / "home"
                root.mkdir(parents=True, exist_ok=True)
                (root / "study-system-users").mkdir(parents=True, exist_ok=True)
                (root / "study-system-users" / "pieye.json").write_text(
                    json.dumps(
                        {
                            "version": 2,
                            "xp": 77,
                            "items": [],
                            "habits": [],
                            "wishlist": [],
                            "logs": [],
                        }
                    ),
                    encoding="utf-8",
                )
                client.cookies.set(self.server.SESSION_COOKIE, "token-pieye")
                migrated = await client.get("/api/data")
                self.assertEqual(migrated.status_code, 200)
                self.assertEqual(migrated.json()["revision"], 1)
                self.assertEqual(migrated.json()["data"]["xp"], 77)
                migrated_again = await client.get("/api/data")
                self.assertEqual(migrated_again.json()["revision"], 1)

                health = await client.get("/api/health")
                self.assertTrue(health.json()["database"]["ok"])

        self.run_async(scenario())

    def test_build_your_own_x_course_preview(self):
        progress_path = Path(os.environ["HERMES_HOME"]) / "home" / "build-your-own-x-progress.json"
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.write_text(
            json.dumps(
                {
                    "course": "Build Your Own X：從零重建技術",
                    "next_lesson": 1,
                    "completed": [],
                    "lessons": {"01": "Distributed Systems", "02": "Web Server"},
                    "lesson_links": {
                        "01": "https://github.com/codecrafters-io/build-your-own-x#build-your-own-distributed-systems",
                        "02": "https://github.com/codecrafters-io/build-your-own-x#build-your-own-web-server",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        async def scenario():
            transport = httpx.ASGITransport(app=self.server.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set(self.server.SESSION_COOKIE, "token-alice")
                response = await client.get("/api/sync-courses")
                self.assertEqual(response.status_code, 200)
                course = response.json()["courses"]["build-your-own-x"]
                self.assertEqual(course["total"], 2)
                self.assertEqual(course["course"], "Build Your Own X：從零重建技術")
                self.assertEqual(course["items"][0]["category"], "Build Your Own X")
                self.assertTrue(course["items"][0]["link"].endswith("#build-your-own-distributed-systems"))

        self.run_async(scenario())


if __name__ == "__main__":
    unittest.main()
