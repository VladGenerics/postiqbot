"""Парсер пула Google-проектов и план синхронизации (scripts/sync_projects.py)."""
from __future__ import annotations

import pytest

from scripts.sync_projects import build_plan, parse

CID1 = "1001-aaa111.apps.googleusercontent.com"
CID2 = "1002-bbb222.apps.googleusercontent.com"
CID3 = "1003-ccc333.apps.googleusercontent.com"
OLD_CID = "9009-zzz999.apps.googleusercontent.com"


class TestParse:
    def test_reads_pairs_from_free_form_text(self):
        raw = f"""
Пул проектов:

1) {CID1} / GOCSPX-secret_one
2. {CID2}   GOCSPX-secret-two
{CID3} — GOCSPX-secret3
"""
        assert parse(raw) == [
            (CID1, "GOCSPX-secret_one"),
            (CID2, "GOCSPX-secret-two"),
            (CID3, "GOCSPX-secret3"),
        ]

    def test_keeps_list_order(self):
        raw = f"{CID2} GOCSPX-b\n{CID1} GOCSPX-a\n"
        assert [cid for cid, _ in parse(raw)] == [CID2, CID1]

    def test_secret_without_client_id_is_fatal(self):
        with pytest.raises(SystemExit):
            parse(f"{CID1} GOCSPX-ok\nGOCSPX-orphan\n")

    def test_client_id_without_secret_is_fatal(self):
        with pytest.raises(SystemExit):
            parse(f"{CID1} GOCSPX-ok\n{CID2}\n")

    def test_duplicate_client_id_is_fatal(self):
        with pytest.raises(SystemExit):
            parse(f"{CID1} GOCSPX-one\n{CID1} GOCSPX-two\n")

    @pytest.mark.parametrize("raw", ["", "   \n\n", "Пул проектов:\nничего тут нет\n"])
    def test_empty_list_is_fatal(self, raw):
        with pytest.raises(SystemExit):
            parse(raw)


class TestBuildPlan:
    def test_update_delete_insert(self):
        pairs = [(CID1, "GOCSPX-1"), (CID2, "GOCSPX-2")]
        rows = [(5, "старое имя", CID1, True), (6, "мёртвый", OLD_CID, True)]
        assert build_plan(pairs, rows, {}) == [
            ("update", 5, "pool-01", CID1),
            ("delete", 6, "мёртвый", OLD_CID),
            ("insert", 0, "pool-02", CID2),
        ]

    def test_project_with_accounts_is_only_disabled(self):
        """Удалить проект, к которому привязаны аккаунты, нельзя."""
        plan = build_plan([(CID1, "GOCSPX-1")], [(6, "живой", OLD_CID, True)], {6: 3})
        assert plan[0] == ("disable", 6, "живой (3 акк.)", OLD_CID)
        assert not [p for p in plan if p[0] == "delete"]

    def test_zero_accounts_counts_as_empty(self):
        plan = build_plan([(CID1, "GOCSPX-1")], [(6, "пустой", OLD_CID, True)], {6: 0})
        assert plan[0][0] == "delete"

    def test_nothing_to_do_but_rename(self):
        rows = [(5, "pool-01", CID1, True), (7, "pool-02", CID2, True)]
        plan = build_plan([(CID1, "GOCSPX-1"), (CID2, "GOCSPX-2")], rows, {})
        assert {p[0] for p in plan} == {"update"}

    def test_empty_pool_gets_everything_inserted(self):
        plan = build_plan([(CID1, "GOCSPX-1"), (CID2, "GOCSPX-2")], [], {})
        assert plan == [
            ("insert", 0, "pool-01", CID1),
            ("insert", 0, "pool-02", CID2),
        ]

    def test_names_are_padded_and_follow_list_order(self):
        pairs = [(f"{1000 + i}-x{i}.apps.googleusercontent.com", "GOCSPX-s") for i in range(1, 11)]
        names = [name for _a, _p, name, _c in build_plan(pairs, [], {})]
        assert names[0] == "pool-01"
        assert names[8] == "pool-09"
        assert names[9] == "pool-10"

    def test_inactive_row_in_wanted_list_is_reactivated(self):
        """Отключённый ранее проект, снова попавший в список, идёт в update — apply_plan включает его обратно."""
        plan = build_plan([(CID1, "GOCSPX-1")], [(5, "pool-01", CID1, False)], {})
        assert plan == [("update", 5, "pool-01", CID1)]
