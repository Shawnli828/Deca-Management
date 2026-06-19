from datetime import datetime, timezone


def column_exists(conn, table, column, is_postgres=False, placeholder="?"):
    if is_postgres:
        row = conn.execute(
            f"""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = {placeholder}
              AND column_name = {placeholder}
            LIMIT 1
            """,
            (table, column),
        ).fetchone()
        return bool(row)

    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(row["name"]) == column for row in rows)


def ensure_column(conn, table, column, definition, is_postgres=False, placeholder="?"):
    if not column_exists(conn, table, column, is_postgres, placeholder):
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except Exception as error:
            message = str(error).lower()
            if "duplicate column" in message or "already exists" in message:
                return
            raise


def schema_migration_applied(conn, version, placeholder="?"):
    row = conn.execute(
        f"SELECT version FROM schema_migrations WHERE version = {placeholder} LIMIT 1",
        (version,),
    ).fetchone()
    return bool(row)


def mark_schema_migration(conn, version, is_postgres=False):
    now = datetime.now(timezone.utc).isoformat()
    if is_postgres:
        conn.execute(
            """
            INSERT INTO schema_migrations (version, applied_at)
            VALUES (%s, %s)
            ON CONFLICT(version) DO UPDATE SET applied_at = EXCLUDED.applied_at
            """,
            (version, now),
        )
        return
    conn.execute(
        "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
        (version, now),
    )


def apply_neutral_source_fields_migration(conn, is_postgres=False, placeholder="?"):
    ensure_column(conn, "accounts", "source", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "accounts", "source_account_id", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "automations", "source", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "automations", "source_automation_id", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "materials", "source", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "materials", "source_material_id", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "posts", "source", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "posts", "source_post_id", "TEXT", is_postgres, placeholder)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_accounts_source_account_id ON accounts(source, source_account_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_automations_source_automation_id ON automations(source, source_automation_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_materials_source_material_id ON materials(source, source_material_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_source_post_id ON posts(source, source_post_id)")
    conn.execute(
        "UPDATE accounts SET source = 'museon_clone' WHERE source IS NULL AND reelfarm_account_id LIKE 'museon:%'"
    )
    conn.execute(
        "UPDATE accounts SET source = 'reelfarm' WHERE source IS NULL AND reelfarm_account_id IS NOT NULL"
    )
    conn.execute(
        "UPDATE accounts SET source_account_id = reelfarm_account_id WHERE source_account_id IS NULL AND reelfarm_account_id IS NOT NULL"
    )
    conn.execute(
        "UPDATE automations SET source = 'museon_clone' WHERE source IS NULL AND reelfarm_automation_id LIKE 'museon:%'"
    )
    conn.execute(
        "UPDATE automations SET source = 'reelfarm' WHERE source IS NULL AND reelfarm_automation_id IS NOT NULL"
    )
    conn.execute(
        "UPDATE automations SET source_automation_id = reelfarm_automation_id WHERE source_automation_id IS NULL AND reelfarm_automation_id IS NOT NULL"
    )
    conn.execute(
        "UPDATE materials SET source = 'museon_clone' WHERE source IS NULL AND reelfarm_video_id LIKE 'museon:%'"
    )
    conn.execute(
        "UPDATE materials SET source = 'reelfarm' WHERE source IS NULL AND reelfarm_video_id IS NOT NULL"
    )
    conn.execute(
        "UPDATE materials SET source_material_id = reelfarm_video_id WHERE source_material_id IS NULL AND reelfarm_video_id IS NOT NULL"
    )
    conn.execute(
        "UPDATE posts SET source = 'museon_clone' WHERE source IS NULL AND reelfarm_post_id LIKE 'museon:%'"
    )
    conn.execute(
        "UPDATE posts SET source = 'reelfarm' WHERE source IS NULL AND reelfarm_post_id IS NOT NULL"
    )
    conn.execute(
        "UPDATE posts SET source_post_id = reelfarm_post_id WHERE source_post_id IS NULL AND reelfarm_post_id IS NOT NULL"
    )


def correct_museon_source_fields_migration(conn, is_postgres=False, placeholder="?"):
    conn.execute(
        "UPDATE accounts SET source = 'museon_clone' WHERE reelfarm_account_id LIKE 'museon:%'"
    )
    conn.execute(
        "UPDATE automations SET source = 'museon_clone' WHERE reelfarm_automation_id LIKE 'museon:%'"
    )
    conn.execute(
        "UPDATE materials SET source = 'museon_clone' WHERE reelfarm_video_id LIKE 'museon:%'"
    )
    conn.execute(
        "UPDATE posts SET source = 'museon_clone' WHERE reelfarm_post_id LIKE 'museon:%'"
    )


SCHEMA_MIGRATIONS = (
    ("2026_06_18_neutral_source_fields", apply_neutral_source_fields_migration),
    ("2026_06_18_correct_museon_source_fields", correct_museon_source_fields_migration),
)


def run_schema_migrations(conn, is_postgres=False, placeholder="?"):
    for version, handler in SCHEMA_MIGRATIONS:
        if schema_migration_applied(conn, version, placeholder):
            continue
        handler(conn, is_postgres, placeholder)
        mark_schema_migration(conn, version, is_postgres)


def init_relational_schema(conn, is_postgres=False, placeholder="?"):
    statements = [
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            owner_type TEXT,
            logo_url TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS markets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_markets (
            id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            market_id TEXT NOT NULL,
            UNIQUE(product_id, market_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_market_channels (
            id TEXT PRIMARY KEY,
            product_market_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            UNIQUE(product_market_id, channel_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            product_market_channel_id TEXT NOT NULL,
            reelfarm_account_id TEXT,
            username TEXT,
            display_name TEXT,
            avatar_url TEXT,
            status TEXT,
            UNIQUE(product_market_channel_id, reelfarm_account_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS automations (
            id TEXT PRIMARY KEY,
            product_market_channel_id TEXT NOT NULL,
            account_id TEXT,
            reelfarm_automation_id TEXT NOT NULL UNIQUE,
            name TEXT,
            status TEXT,
            schedule TEXT,
            settings_json TEXT,
            post_mode TEXT,
            publish_method TEXT,
            sync_status TEXT,
            last_seen_at TEXT,
            deleted_at TEXT,
            created_at TEXT,
            synced_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            UNIQUE(product_id, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS formats (
            id TEXT PRIMARY KEY,
            concept_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            UNIQUE(concept_id, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS materials (
            id TEXT PRIMARY KEY,
            automation_id TEXT NOT NULL,
            product_market_channel_id TEXT NOT NULL,
            account_id TEXT,
            concept_id TEXT,
            format_id TEXT,
            reelfarm_video_id TEXT NOT NULL UNIQUE,
            video_type TEXT,
            hook TEXT,
            prompt TEXT,
            images_json TEXT,
            slide_count INTEGER,
            status TEXT,
            created_at TEXT,
            finished_at TEXT,
            synced_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            material_id TEXT NOT NULL,
            account_id TEXT,
            reelfarm_post_id TEXT NOT NULL UNIQUE,
            status TEXT,
            title TEXT,
            published_at TEXT,
            published_at_readable TEXT,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            share_count INTEGER,
            bookmark_count INTEGER,
            synced_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS post_daily_snapshots (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            share_count INTEGER,
            bookmark_count INTEGER,
            synced_at TEXT NOT NULL,
            UNIQUE(post_id, snapshot_date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS account_tags (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(account_id, tag)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS account_issues (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            issue TEXT NOT NULL,
            source TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(account_id, issue)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_tags (
            id TEXT PRIMARY KEY,
            product_code TEXT NOT NULL,
            tag TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(product_code, tag)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_daily_growth_snapshots (
            id TEXT PRIMARY KEY,
            product_code TEXT NOT NULL,
            report_date TEXT NOT NULL,
            report_timezone TEXT NOT NULL,
            source_timezone TEXT NOT NULL,
            utc_start TEXT NOT NULL,
            utc_end TEXT NOT NULL,
            source_date_from TEXT,
            source_date_to TEXT,
            reelfarm_views INTEGER,
            clone_views INTEGER,
            total_views INTEGER,
            download_count INTEGER,
            onboarding_unique INTEGER,
            synced_at TEXT NOT NULL,
            UNIQUE(product_code, report_date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sync_runs (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            product_code TEXT,
            country_code TEXT,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            duration_seconds REAL,
            records_count INTEGER,
            error TEXT,
            meta_json TEXT
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_post_daily_snapshots_snapshot_date ON post_daily_snapshots(snapshot_date)",
        "CREATE INDEX IF NOT EXISTS idx_post_daily_snapshots_post_id ON post_daily_snapshots(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_account_tags_account_id ON account_tags(account_id)",
        "CREATE INDEX IF NOT EXISTS idx_account_tags_tag ON account_tags(tag)",
        "CREATE INDEX IF NOT EXISTS idx_account_issues_account_id ON account_issues(account_id)",
        "CREATE INDEX IF NOT EXISTS idx_account_issues_issue ON account_issues(issue)",
        "CREATE INDEX IF NOT EXISTS idx_product_tags_product_code ON product_tags(product_code)",
        "CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at)",
        "CREATE INDEX IF NOT EXISTS idx_posts_material_id ON posts(material_id)",
        "CREATE INDEX IF NOT EXISTS idx_materials_automation_id ON materials(automation_id)",
        "CREATE INDEX IF NOT EXISTS idx_automations_product_market_channel_id ON automations(product_market_channel_id)",
        "CREATE INDEX IF NOT EXISTS idx_product_daily_growth_snapshots_product_date ON product_daily_growth_snapshots(product_code, report_date)",
        "CREATE INDEX IF NOT EXISTS idx_product_daily_growth_snapshots_report_date ON product_daily_growth_snapshots(report_date)",
        "CREATE INDEX IF NOT EXISTS idx_sync_runs_source_finished_at ON sync_runs(source, finished_at)",
        "CREATE INDEX IF NOT EXISTS idx_sync_runs_product_source_finished_at ON sync_runs(product_code, source, finished_at)",
    ]
    for statement in statements:
        conn.execute(statement)
    ensure_column(conn, "automations", "post_mode", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "automations", "publish_method", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "automations", "sync_status", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "automations", "last_seen_at", "TEXT", is_postgres, placeholder)
    ensure_column(conn, "automations", "deleted_at", "TEXT", is_postgres, placeholder)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_automations_sync_status ON automations(sync_status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_automations_pmc_sync_status ON automations(product_market_channel_id, sync_status)"
    )
    run_schema_migrations(conn, is_postgres, placeholder)
