#!/usr/bin/env python
import os
import json
import glob
import logging

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


load_dotenv()

# 데이터베이스 연결 정보
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": 5432,
    "user": os.getenv("POSTGRES_USER", "searchright"),
    "password": os.getenv("POSTGRES_PASSWORD", "searchright"),
    "database": os.getenv("POSTGRES_DB", "searchright"),
}


def connect_to_db():
    """데이터베이스에 연결"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info(f"성공적으로 {DB_CONFIG['database']} 데이터베이스에 연결했습니다.")
        return conn
    except psycopg2.Error as e:
        logger.error(f"데이터베이스 연결 오류: {e}")
        raise


def create_company_table(conn):
    """company 테이블 생성 (존재하지 않을 경우)"""
    try:
        with conn.cursor() as cursor:
            # 테이블이 존재하는지 확인
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'company'
                );
            """
            )
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                logger.info(
                    "company 테이블이 존재하지 않습니다. 새로운 테이블을 생성합니다."
                )
                cursor.execute(
                    """
                    CREATE TABLE company (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        data JSONB NOT NULL
                    );
                """
                )
                logger.info("company 테이블이 성공적으로 생성되었습니다.")
            else:
                logger.info(
                    "company 테이블이 이미 존재합니다. 테이블 생성을 건너뜁니다."
                )
    except psycopg2.Error as e:
        logger.error(f"테이블 생성 오류: {e}")
        raise


def load_company_data(file_path):
    """회사 데이터 파일 불러오기"""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            # 파일 이름에서 회사 이름 추출 (예: company_ex1_비바리퍼블리카.json -> 비바리퍼블리카)
            company_name = os.path.basename(file_path).split("_")[-1].split(".")[0]
            return company_name, data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"파일 로드 오류 ({file_path}): {e}")
        return None, None


def insert_company_data(conn, name, data):
    """회사 데이터를 데이터베이스에 삽입"""
    try:
        with conn.cursor() as cursor:
            # 이미 존재하는지 확인
            cursor.execute("SELECT COUNT(*) FROM company WHERE name = %s", (name,))
            count = cursor.fetchone()[0]

            if count > 0:
                logger.info(
                    f"회사 '{name}'의 데이터가 이미 존재합니다. 삽입을 건너뜁니다."
                )
                return False

            # 데이터 삽입
            cursor.execute(
                "INSERT INTO company (name, data) VALUES (%s, %s)",
                (name, json.dumps(data)),
            )
            logger.info(f"회사 '{name}'의 데이터가 성공적으로 삽입되었습니다.")
            return True
    except psycopg2.Error as e:
        logger.error(f"데이터 삽입 오류: {e}")
        conn.rollback()
        return False


def main():
    """메인 함수"""
    try:
        # 데이터베이스 연결
        conn = connect_to_db()

        # company 테이블 생성
        create_company_table(conn)

        # 회사 데이터 파일 찾기
        base_dir = os.path.dirname(__file__)
        pattern = os.path.join(base_dir, 'company_ex*.json')
        company_files = glob.glob(pattern)
        logger.info(f"{len(company_files)}개의 회사 데이터 파일을 찾았습니다.")

        # 데이터 처리 및 삽입
        success_count = 0
        for file_path in sorted(company_files):
            company_name, company_data = load_company_data(file_path)
            if company_name and company_data:
                if insert_company_data(conn, company_name, company_data):
                    success_count += 1

        logger.info(f"총 {success_count}개의 회사 데이터가 성공적으로 삽입되었습니다.")

    except Exception as e:
        logger.error(f"예상치 못한 오류가 발생했습니다: {e}")
    finally:
        if "conn" in locals() and conn:
            conn.close()
            logger.info("데이터베이스 연결이 닫혔습니다.")


if __name__ == "__main__":
    main()
