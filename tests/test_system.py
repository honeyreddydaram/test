import tempfile
import unittest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.model import State, Parameters, update, decayed, predict, project
from backend.engine import SKILLS, ITEMS, check, recommend, validate_generated
from backend.simulation import metrics, run
from backend import app as module


class KnowledgeTests(unittest.TestCase):
    def test_bayes_hand_calculation(self):
        m = 0.35 * 0.9 / (0.35 * 0.9 + 0.65 * 0.2)
        self.assertAlmostEqual(update(State(), True, 100).mastery, m + (1 - m) * 0.12)

    def test_incorrect_and_hint_evidence(self):
        self.assertLess(update(State(), False, 100).mastery, 0.35)
        self.assertLess(
            update(State(), True, 100, hints=1).mastery,
            update(State(), True, 100).mastery,
        )

    def test_forgetting(self):
        self.assertAlmostEqual(
            decayed(State(mastery=0.8, last_practiced=0), 30 * 86400), 0.4
        )
        self.assertEqual(decayed(State(mastery=0.8, last_practiced=100), 0), 0.8)

    def test_projection_and_probabilities(self):
        self.assertAlmostEqual(project(State(), 0, 0), 0.35)
        self.assertGreater(project(State(), 3, 0), 0.35)
        for s in (State(mastery=0), State(mastery=1)):
            self.assertTrue(0 <= predict(s, 0) <= 1)

    def test_graph_is_acyclic_and_errors_unique(self):
        visited = set()
        active = set()
        errors = []

        def visit(k):
            self.assertNotIn(k, active)
            if k in visited:
                return
            active.add(k)
            for p in SKILLS[k]["prerequisites"]:
                visit(p)
            active.remove(k)
            visited.add(k)

        for k, s in SKILLS.items():
            visit(k)
            errors.extend(e["id"] for e in s["errors"])
        self.assertEqual(len(errors), len(set(errors)))

    def test_soft_prerequisites_do_not_lock_advanced_skill(self):
        states = {key: State(mastery=0.99, attempts=20) for key in SKILLS}
        states["conditionals"] = State()
        states["past"] = State(mastery=0.1, attempts=20)
        item, _, reason = recommend(states, 0)
        self.assertEqual(item["skill"], "conditionals")
        self.assertIn("no skill is locked", reason)
        hard_item, _, _ = recommend(states, 0, prerequisite_mode="hard")
        self.assertNotEqual(hard_item["skill"], "conditionals")

    def test_repeated_item_has_less_influence(self):
        fresh = update(State(), True, 0)
        repeated = update(State(), True, 0, evidence_weight=0.2)
        self.assertLess(repeated.mastery, fresh.mastery)


class CheckerTests(unittest.TestCase):
    def test_bank_coverage_and_distinct_prompts(self):
        self.assertEqual(len({item["id"] for item in ITEMS}), len(ITEMS))
        for skill in SKILLS:
            bank = [
                item
                for item in ITEMS
                if item["skill"] == skill and item["type"] != "writing"
            ]
            self.assertGreaterEqual(len(bank), 5)
            self.assertEqual(len({item["prompt"] for item in bank}), len(bank))

    def test_suffix_variants_and_normalization(self):
        item = next(item for item in ITEMS if item["id"] == "item-4")
        for answer in ("ness", "kindness", " Kindness! "):
            self.assertTrue(check(item, answer)["correct"])
        self.assertFalse(check(item, "unkindness")["correct"])

    def test_item_rotation_exhausts_unseen_before_repeating(self):
        states = {key: State(mastery=0.99, attempts=20) for key in SKILLS}
        states["past"] = State(mastery=0.82)
        counts = {}
        seen = []
        for _ in range(5):
            item, _, _ = recommend(states, 0, item_counts=counts)
            self.assertEqual(item["skill"], "past")
            seen.append(item["id"])
            counts[item["id"]] = counts.get(item["id"], 0) + 1
        self.assertEqual(len(set(seen)), 5)

    def test_seed_keys_and_taxonomy(self):
        for item in ITEMS:
            if item["type"] == "writing":
                continue
            for answer in item["answers"]:
                self.assertTrue(check(item, answer)["correct"])
            allowed = {e["id"] for e in SKILLS[item["skill"]]["errors"]}
            for answer, error in item["distractors"].items():
                self.assertIn(error, allowed)
                self.assertEqual(check(item, answer)["error"], error)
                self.assertFalse(check(item, answer)["correct"])

    def test_writing_and_unknown(self):
        self.assertIsNone(check(ITEMS[-1], "Yesterday I went home.")["correct"])
        self.assertEqual(check(ITEMS[0], "random text")["error"], "unclassified")

    def test_policy_explores_when_nothing_is_in_zone(self):
        states = {"bases": State(mastery=0.99, attempts=20, last_practiced=0)}
        item, _, reason = recommend(states, 0)
        self.assertNotEqual(item["skill"], "bases")
        self.assertIn("explore", reason)

    def test_optional_generation_adapter(self):
        from backend.generation import generate

        item = ITEMS[0].copy()
        item["explanation"] = SKILLS[item["skill"]]["rule"]
        self.assertEqual(generate(lambda: item)["answers"], ITEMS[0]["answers"])
        item["explanation"] = "Invented explanation"
        with self.assertRaises(ValueError):
            generate(lambda: item)

    def test_generation_cannot_supply_key(self):
        item = ITEMS[0].copy()
        item["answers"] = ["wrong"]
        self.assertEqual(validate_generated(item)["answers"], ITEMS[0]["answers"])
        item["prompt"] = "invented"
        with self.assertRaises(ValueError):
            validate_generated(item)

    def test_metrics(self):
        m = metrics([0.1, 0.9], [0, 1])
        self.assertEqual(m["auc"], 1)
        self.assertAlmostEqual(m["brier"], 0.01)
        self.assertEqual(metrics([0.5, 0.5], [0, 1])["auc"], 0.5)

    def test_simulator_reproducible(self):
        self.assertEqual(run(1, 2, 8), run(1, 2, 8))


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        module.DB = str(Path(self.tmp.name) / "db.sqlite")
        self.client = TestClient(module.app)
        self.token = self.client.post("/api/session").json()["token"]
        self.headers = {"Authorization": "Bearer " + self.token}

    def tearDown(self):
        self.tmp.cleanup()

    def test_auth(self):
        self.assertEqual(self.client.get("/api/state").status_code, 401)

    def test_lifecycle_no_key_leak_no_answer_storage(self):
        task = self.client.get("/api/next", headers=self.headers).json()
        self.assertNotIn("answers", task["exercise"])
        self.assertNotIn("distractors", task["exercise"])
        data = {"attempt_id": task["attempt_id"]}
        self.assertEqual(
            self.client.post("/api/hint", headers=self.headers, json=data).status_code,
            200,
        )
        data["answer"] = "PRIVATE_TEXT_MUST_NOT_PERSIST"
        self.assertEqual(
            self.client.post(
                "/api/answer", headers=self.headers, json=data
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                "/api/answer", headers=self.headers, json=data
            ).status_code,
            409,
        )
        state = self.client.get("/api/export", headers=self.headers).json()
        self.assertEqual(state["events"][0]["hints"], 1)
        self.assertNotIn("PRIVATE_TEXT", json.dumps(state))
        self.assertNotIn(b"PRIVATE_TEXT", Path(module.DB).read_bytes())
        self.assertEqual(
            self.client.delete("/api/session", headers=self.headers).status_code, 200
        )
        self.assertEqual(
            self.client.get("/api/state", headers=self.headers).status_code, 401
        )

    def test_writing_is_unscored_and_not_stored(self):
        task = self.client.get("/api/next?writing=true", headers=self.headers).json()
        result = self.client.post(
            "/api/answer",
            headers=self.headers,
            json={"attempt_id": task["attempt_id"], "answer": "PRIVATE_STORY"},
        ).json()
        self.assertIsNone(task["predicted_success"])
        self.assertIsNone(result["correct"])
        state = self.client.get("/api/state", headers=self.headers).json()
        self.assertEqual(state["skills"]["past"]["attempts"], 0)
        self.assertNotIn(b"PRIVATE_STORY", Path(module.DB).read_bytes())

    def test_server_tracks_item_rotation_and_repeat_weight(self):
        from backend.engine import ITEM_MAP

        with module.db() as conn:
            conn.execute(
                "INSERT INTO issued(id,token,item,started,used) VALUES(?,?,?,?,1)",
                ("old", self.token, "item-4", 0),
            )
            conn.execute(
                "INSERT INTO issued(id,token,item,started) VALUES(?,?,?,?)",
                ("repeat", self.token, "item-4", 0),
            )
        response = self.client.post(
            "/api/answer",
            headers=self.headers,
            json={"attempt_id": "repeat", "answer": "kindness"},
        )
        self.assertTrue(response.json()["correct"])
        events = self.client.get("/api/export", headers=self.headers).json()["events"]
        self.assertEqual(events[-1]["item"], "item-4")
        self.assertEqual(events[-1]["evidence_weight"], 0.5)

    def test_export_all_history(self):
        with module.db() as conn:
            for n in range(23):
                conn.execute(
                    "INSERT INTO events VALUES (?,?)",
                    (
                        self.token,
                        json.dumps({"skill": "past", "correct": True, "at": n}),
                    ),
                )
        self.assertEqual(
            len(self.client.get("/api/export", headers=self.headers).json()["events"]),
            23,
        )

    def test_built_frontend_when_present(self):
        if module.DIST.exists():
            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertIn("Grammar Garden", response.text)

    def test_session_isolation_and_scenario_validation(self):
        task = self.client.get("/api/next", headers=self.headers).json()
        other = self.client.post("/api/session").json()["token"]
        self.assertEqual(
            self.client.post(
                "/api/answer",
                headers={"Authorization": "Bearer " + other},
                json={"attempt_id": task["attempt_id"], "answer": "a"},
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                "/api/simulate",
                headers=self.headers,
                json={"skill": "articles", "sessions": -1},
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                "/api/simulate",
                headers=self.headers,
                json={"skill": "articles", "sessions": 3},
            ).status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()
