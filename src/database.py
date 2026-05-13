import psycopg2
from psycopg2 import pool
from typing import Optional
from src.config import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,
    CONSULT_DB_HOST, CONSULT_DB_PORT, CONSULT_DB_USER, CONSULT_DB_PASSWORD, CONSULT_DB_NAME,
)
from logging import getLogger

logger = getLogger(name="database")

connection_pool = None
consult_connection_pool = None


def init_connection_pool():
    global connection_pool
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print("Database connection pool initialized")
    except Exception as e:
        print(f"Failed to initialize connection pool: {e}")
        raise


def init_consult_connection_pool():
    global consult_connection_pool
    try:
        consult_connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=CONSULT_DB_HOST,
            port=CONSULT_DB_PORT,
            user=CONSULT_DB_USER,
            password=CONSULT_DB_PASSWORD,
            database=CONSULT_DB_NAME
        )
        print("Consult database connection pool initialized")
    except Exception as e:
        print(f"Failed to initialize consult connection pool: {e}")
        raise


def get_connection():
    if connection_pool is None:
        init_connection_pool()
    return connection_pool.getconn()


def get_consult_connection():
    if consult_connection_pool is None:
        init_consult_connection_pool()
    return consult_connection_pool.getconn()


def return_connection(conn):
    if connection_pool is not None:
        connection_pool.putconn(conn)


def return_consult_connection(conn):
    if consult_connection_pool is not None:
        consult_connection_pool.putconn(conn)


def close_all_connections():
    if connection_pool is not None:
        connection_pool.closeall()
        print("All database connections closed")
    if consult_connection_pool is not None:
        consult_connection_pool.closeall()
        print("All consult database connections closed")


def get_consult_data_by_org_and_date(org_id: str, date: str) -> list[dict]:
    """Query consult table returning all rows matching organization_id and date (cast to date)."""
    conn = None
    try:
        conn = get_consult_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                organization_id,
                created_at,
                conv_date,
                dialog,
                score_1_start_and_relevance,
                score_2_request_understanding_and_relevance,
                score_3_dialog_logic,
                score_4_objection_handling,
                score_5_solution_promotion,
                score_6_cta_and_result_fixation,
                score_7_service_and_wording,
                score_8_niche_constraints,
                score_9_result_and_risk,
                "Reason",
                "Result"
            FROM public.conversation_scores
            WHERE organization_id = %s
              AND conv_date = %s::date
            ORDER BY created_at
            """,
            (org_id, date),
        )
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        logger.info("Consult query returned %d rows", len(rows))
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Consult database error: {e}")
        raise
    finally:
        if conn:
            return_consult_connection(conn)


def get_record_by_filename(filename: str) -> Optional[dict]:
    """
    Query the callsense table and return transcription for the given filename.
    Returns a dictionary with the transcription or None if not found.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT transcription, dialogs FROM public.callsense WHERE filename = %s LIMIT 1"
        cursor.execute(query, (filename,))
        
        result = cursor.fetchone()
        cursor.close()
        
        logger.info(result)
        
        if result:
            return {"filename": filename, "transcription": result[0], "dialogs": result[1]}
        return None
        
    except Exception as e:
        print(f"Database error: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)
