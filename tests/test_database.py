"""Unit tests for src/database.py — all psycopg2 calls are mocked."""
import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest
import psycopg2

import src.database as db_module
from src.database import (
    init_connection_pool,
    init_consult_connection_pool,
    get_connection,
    get_consult_connection,
    return_connection,
    return_consult_connection,
    close_all_connections,
    get_record_by_filename,
    get_consult_data_by_org_and_date,
)


@pytest.fixture(autouse=True)
def reset_pools():
    """Reset both pool globals before and after every test."""
    db_module.connection_pool = None
    db_module.consult_connection_pool = None
    yield
    db_module.connection_pool = None
    db_module.consult_connection_pool = None


def make_pool_mock():
    pool = MagicMock()
    conn = MagicMock()
    pool.getconn.return_value = conn
    return pool, conn


# ---------------------------------------------------------------------------
# init_connection_pool
# ---------------------------------------------------------------------------

class TestInitConnectionPool:
    def test_creates_pool_with_correct_args(self):
        with patch("src.database.psycopg2") as mock_pg:
            init_connection_pool()
            mock_pg.pool.SimpleConnectionPool.assert_called_once_with(
                1, 20,
                host=db_module.DB_HOST,
                port=db_module.DB_PORT,
                user=db_module.DB_USER,
                password=db_module.DB_PASSWORD,
                database=db_module.DB_NAME,
            )

    def test_assigns_pool_global(self):
        with patch("src.database.psycopg2") as mock_pg:
            fake_pool = MagicMock()
            mock_pg.pool.SimpleConnectionPool.return_value = fake_pool
            init_connection_pool()
            assert db_module.connection_pool is fake_pool

    def test_raises_on_connection_failure(self):
        with patch("src.database.psycopg2") as mock_pg:
            mock_pg.pool.SimpleConnectionPool.side_effect = psycopg2.OperationalError("refused")
            with pytest.raises(psycopg2.OperationalError):
                init_connection_pool()

    def test_pool_remains_none_after_failure(self):
        with patch("src.database.psycopg2") as mock_pg:
            mock_pg.pool.SimpleConnectionPool.side_effect = Exception("bad")
            with pytest.raises(Exception):
                init_connection_pool()
            assert db_module.connection_pool is None


# ---------------------------------------------------------------------------
# init_consult_connection_pool
# ---------------------------------------------------------------------------

class TestInitConsultConnectionPool:
    def test_creates_pool_with_correct_args(self):
        with patch("src.database.psycopg2") as mock_pg:
            init_consult_connection_pool()
            mock_pg.pool.SimpleConnectionPool.assert_called_once_with(
                1, 20,
                host=db_module.CONSULT_DB_HOST,
                port=db_module.CONSULT_DB_PORT,
                user=db_module.CONSULT_DB_USER,
                password=db_module.CONSULT_DB_PASSWORD,
                database=db_module.CONSULT_DB_NAME,
            )

    def test_assigns_consult_pool_global(self):
        with patch("src.database.psycopg2") as mock_pg:
            fake_pool = MagicMock()
            mock_pg.pool.SimpleConnectionPool.return_value = fake_pool
            init_consult_connection_pool()
            assert db_module.consult_connection_pool is fake_pool

    def test_raises_on_connection_failure(self):
        with patch("src.database.psycopg2") as mock_pg:
            mock_pg.pool.SimpleConnectionPool.side_effect = psycopg2.OperationalError("refused")
            with pytest.raises(psycopg2.OperationalError):
                init_consult_connection_pool()


# ---------------------------------------------------------------------------
# get_connection / get_consult_connection
# ---------------------------------------------------------------------------

class TestGetConnection:
    def test_returns_conn_from_pool(self):
        pool, conn = make_pool_mock()
        db_module.connection_pool = pool
        assert get_connection() is conn

    def test_auto_inits_pool_when_none(self):
        with patch("src.database.init_connection_pool") as mock_init:
            pool, conn = make_pool_mock()
            def set_pool():
                db_module.connection_pool = pool
            mock_init.side_effect = set_pool
            result = get_connection()
            mock_init.assert_called_once()
            assert result is conn

    def test_calls_getconn(self):
        pool, conn = make_pool_mock()
        db_module.connection_pool = pool
        get_connection()
        pool.getconn.assert_called_once()


class TestGetConsultConnection:
    def test_returns_conn_from_pool(self):
        pool, conn = make_pool_mock()
        db_module.consult_connection_pool = pool
        assert get_consult_connection() is conn

    def test_auto_inits_pool_when_none(self):
        with patch("src.database.init_consult_connection_pool") as mock_init:
            pool, conn = make_pool_mock()
            def set_pool():
                db_module.consult_connection_pool = pool
            mock_init.side_effect = set_pool
            result = get_consult_connection()
            mock_init.assert_called_once()
            assert result is conn


# ---------------------------------------------------------------------------
# return_connection / return_consult_connection
# ---------------------------------------------------------------------------

class TestReturnConnection:
    def test_calls_putconn(self):
        pool, conn = make_pool_mock()
        db_module.connection_pool = pool
        return_connection(conn)
        pool.putconn.assert_called_once_with(conn)

    def test_no_op_when_pool_is_none(self):
        # Should not raise even with no pool initialised.
        return_connection(MagicMock())


class TestReturnConsultConnection:
    def test_calls_putconn(self):
        pool, conn = make_pool_mock()
        db_module.consult_connection_pool = pool
        return_consult_connection(conn)
        pool.putconn.assert_called_once_with(conn)

    def test_no_op_when_pool_is_none(self):
        return_consult_connection(MagicMock())


# ---------------------------------------------------------------------------
# close_all_connections
# ---------------------------------------------------------------------------

class TestCloseAllConnections:
    def test_closes_both_pools(self):
        pool1, _ = make_pool_mock()
        pool2, _ = make_pool_mock()
        db_module.connection_pool = pool1
        db_module.consult_connection_pool = pool2
        close_all_connections()
        pool1.closeall.assert_called_once()
        pool2.closeall.assert_called_once()

    def test_no_op_when_both_none(self):
        # Should not raise.
        close_all_connections()

    def test_closes_only_main_when_consult_none(self):
        pool, _ = make_pool_mock()
        db_module.connection_pool = pool
        close_all_connections()
        pool.closeall.assert_called_once()

    def test_closes_only_consult_when_main_none(self):
        pool, _ = make_pool_mock()
        db_module.consult_connection_pool = pool
        close_all_connections()
        pool.closeall.assert_called_once()


# ---------------------------------------------------------------------------
# get_record_by_filename
# ---------------------------------------------------------------------------

class TestGetRecordByFilename:
    def _setup_pool(self, fetchone_return):
        pool, conn = make_pool_mock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = fetchone_return
        db_module.connection_pool = pool
        return pool, conn, cursor

    def test_returns_dict_when_found(self):
        self._setup_pool(("hello world", '{"a":1}'))
        result = get_record_by_filename("test.mp3")
        assert result == {
            "filename": "test.mp3",
            "transcription": "hello world",
            "dialogs": '{"a":1}',
        }

    def test_returns_none_when_not_found(self):
        self._setup_pool(None)
        assert get_record_by_filename("missing.mp3") is None

    def test_executes_correct_query(self):
        _, _, cursor = self._setup_pool(None)
        get_record_by_filename("file.mp3")
        sql, params = cursor.execute.call_args[0]
        assert "public.callsense" in sql
        assert "filename" in sql
        assert params == ("file.mp3",)

    def test_connection_returned_on_success(self):
        pool, conn, _ = self._setup_pool(None)
        get_record_by_filename("file.mp3")
        pool.putconn.assert_called_once_with(conn)

    def test_connection_returned_on_db_error(self):
        pool, conn = make_pool_mock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = Exception("db error")
        db_module.connection_pool = pool
        with pytest.raises(Exception, match="db error"):
            get_record_by_filename("file.mp3")
        pool.putconn.assert_called_once_with(conn)

    def test_cursor_closed_after_query(self):
        _, _, cursor = self._setup_pool(("t", "d"))
        get_record_by_filename("file.mp3")
        cursor.close.assert_called_once()

    def test_null_transcription_and_dialogs(self):
        self._setup_pool((None, None))
        result = get_record_by_filename("file.mp3")
        assert result == {"filename": "file.mp3", "transcription": None, "dialogs": None}


# ---------------------------------------------------------------------------
# get_consult_data_by_org_and_date
# ---------------------------------------------------------------------------

ORG_ID = str(uuid.uuid4())
ROW_ID = str(uuid.uuid4())
CREATED_AT = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

FAKE_COLUMNS = [
    "id", "organization_id", "created_at", "conv_date", "dialog",
    "score_1_start_and_relevance", "score_2_request_understanding_and_relevance",
    "score_3_dialog_logic", "score_4_objection_handling", "score_5_solution_promotion",
    "score_6_cta_and_result_fixation", "score_7_service_and_wording",
    "score_8_niche_constraints", "score_9_result_and_risk",
]
FAKE_ROW = (
    ROW_ID, ORG_ID, CREATED_AT, date(2024, 1, 15), "Hello",
    4, 3, 5, None, 2, 4, 5, None, 3,
)


class TestGetConsultDataByOrgAndDate:
    def _setup_pool(self, rows):
        pool, conn = make_pool_mock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.description = [(col,) for col in FAKE_COLUMNS]
        cursor.fetchall.return_value = rows
        db_module.consult_connection_pool = pool
        return pool, conn, cursor

    def test_returns_list_of_dicts(self):
        self._setup_pool([FAKE_ROW])
        result = get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        assert len(result) == 1
        assert result[0]["dialog"] == "Hello"
        assert result[0]["organization_id"] == ORG_ID

    def test_empty_result(self):
        self._setup_pool([])
        result = get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        assert result == []

    def test_all_columns_present(self):
        self._setup_pool([FAKE_ROW])
        result = get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        assert set(result[0].keys()) == set(FAKE_COLUMNS)

    def test_nullable_scores_preserved(self):
        self._setup_pool([FAKE_ROW])
        result = get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        assert result[0]["score_4_objection_handling"] is None
        assert result[0]["score_8_niche_constraints"] is None

    def test_executes_query_with_correct_params(self):
        _, _, cursor = self._setup_pool([])
        get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        sql, params = cursor.execute.call_args[0]
        assert "public.conversation_scores" in sql
        assert "organization_id" in sql
        assert "conv_date" in sql
        assert params == (ORG_ID, "2024-01-15")

    def test_connection_returned_on_success(self):
        pool, conn, _ = self._setup_pool([])
        get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        pool.putconn.assert_called_once_with(conn)

    def test_connection_returned_on_db_error(self):
        pool, conn = make_pool_mock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = Exception("timeout")
        db_module.consult_connection_pool = pool
        with pytest.raises(Exception, match="timeout"):
            get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        pool.putconn.assert_called_once_with(conn)

    def test_multiple_rows_returned(self):
        self._setup_pool([FAKE_ROW, FAKE_ROW])
        result = get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        assert len(result) == 2

    def test_cursor_closed_after_query(self):
        _, _, cursor = self._setup_pool([FAKE_ROW])
        get_consult_data_by_org_and_date(ORG_ID, "2024-01-15")
        cursor.close.assert_called_once()
