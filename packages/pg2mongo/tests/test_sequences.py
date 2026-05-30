from pg2mongo.sequences import ensure_counter, get_next_sequence


class _FakeCounters:
    def __init__(self):
        self.docs: dict = {}

    def find_one(self, query, projection=None, sort=None, session=None):
        _id = query.get("_id")
        if _id is not None and not isinstance(_id, dict):
            return self.docs.get(_id)
        return None

    def update_one(self, query, update, upsert=False, session=None):
        _id = query["_id"]
        if _id in self.docs:
            return
        if upsert and "$setOnInsert" in update:
            self.docs[_id] = dict(update["$setOnInsert"])

    def find_one_and_update(self, query, update, return_document=None, session=None):
        _id = query["_id"]
        if _id not in self.docs:
            return None
        self.docs[_id]["sequenceValue"] += update["$inc"]["sequenceValue"]
        return dict(self.docs[_id])


class _FakePickups:
    def find_one(self, query, sort=None, projection=None, session=None):
        return None


class _FakeDB:
    def __init__(self):
        self.counters = _FakeCounters()
        self.pickups = _FakePickups()

    def __getitem__(self, name):
        if name == "counters":
            return self.counters
        if name == "pickups":
            return self.pickups
        raise KeyError(name)


def test_get_next_sequence_auto_creates_counter():
    db = _FakeDB()
    assert get_next_sequence(db, "pickup_id") == 1
    assert get_next_sequence(db, "pickup_id") == 2


def test_ensure_counter_idempotent():
    db = _FakeDB()
    ensure_counter(db, "pickup_id", initial=10)
    ensure_counter(db, "pickup_id", initial=99)
    assert db.counters.docs["pickup_id"]["sequenceValue"] == 10
