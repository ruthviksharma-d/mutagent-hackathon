"""
Diagnostic script to test MySQL connectivity and auto-create/update tables.
"""
import pymysql
from config.settings import get_settings

def check_connection():
    settings = get_settings()
    print(f"Testing MySQL connection to {settings.DB_HOST}:{settings.DB_PORT} as user '{settings.DB_USER}'...")
    try:
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )
        print("[OK] Connected to MySQL server successfully!")
        
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES;")
            dbs = [row[0] for row in cursor.fetchall()]
            if settings.DB_NAME in dbs:
                print(f"[OK] Database '{settings.DB_NAME}' exists.")
            else:
                print(f"[+] Database '{settings.DB_NAME}' does not exist. Creating database...")
                cursor.execute(f"CREATE DATABASE `{settings.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                print(f"[OK] Database '{settings.DB_NAME}' created successfully!")
            
            # Switch to database and check org_settings columns
            conn.select_db(settings.DB_NAME)
            cursor.execute("SHOW TABLES LIKE 'org_settings';")
            if cursor.fetchone():
                cursor.execute("SHOW COLUMNS FROM org_settings LIKE 'risk_weights';")
                if not cursor.fetchone():
                    print("[+] Adding missing 'risk_weights' column to org_settings table...")
                    cursor.execute("ALTER TABLE org_settings ADD COLUMN risk_weights JSON NULL;")
                cursor.execute("SHOW COLUMNS FROM org_settings LIKE 'enabled_analyzers';")
                if not cursor.fetchone():
                    print("[+] Adding missing 'enabled_analyzers' column to org_settings table...")
                    cursor.execute("ALTER TABLE org_settings ADD COLUMN enabled_analyzers JSON NULL;")
                print("[OK] org_settings table schema is up to date!")
        conn.close()
        return True

    except pymysql.err.OperationalError as e:
        code, msg = e.args
        if code == 1045:
            print(f"\n[ERROR] AUTHENTICATION FAILED (Error 1045):")
            print(f"   MySQL rejected the password in backend/.env for user '{settings.DB_USER}'.")
            print(f"   Please update DB_PASSWORD in backend/.env with the password you set in MySQL Workbench.")
        else:
            print(f"\n[ERROR] MYSQL ERROR ({code}): {msg}")
        return False
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        return False

if __name__ == "__main__":
    check_connection()
