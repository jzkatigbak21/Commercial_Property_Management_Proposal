import shutil, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app

class Tests(unittest.TestCase):
    def setUp(self):
        for p in (app.RUNS, app.REVIEWS):
            if p.exists(): p.unlink()

    def test_landlord_case(self):
        r = app.process_email({"message_id":"1","from":"tenant1@example.com","subject":"Sink leak","body":"Water is leaking."})
        self.assertEqual(r["workflow_run"]["assessment"]["recommended_responsibility"], "landlord")

    def test_duplicate(self):
        p={"message_id":"2","from":"tenant1@example.com","subject":"Leak","body":"Water leak"}
        self.assertFalse(app.process_email(p)["duplicate"])
        self.assertTrue(app.process_email(p)["duplicate"])

    def test_unknown_sender_review(self):
        r=app.process_email({"message_id":"3","from":"unknown@example.com","subject":"Issue","body":"Please help"})
        self.assertEqual(r["workflow_run"]["status"], "manual_review")

    def test_emergency_review(self):
        r=app.process_email({"message_id":"4","from":"tenant1@example.com","subject":"Burst pipe","body":"The unit is flooding"})
        self.assertEqual(r["workflow_run"]["status"], "manual_review")

if __name__ == "__main__":
    unittest.main()
