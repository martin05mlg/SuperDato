import sqlite3


def migrate():
    conn = sqlite3.connect("superdato_dev.db")
    c = conn.cursor()

    # 1. Update households
    c.execute("PRAGMA table_info(households)")
    h_cols = [r[1] for r in c.fetchall()]
    if "settings" not in h_cols:
        c.execute("ALTER TABLE households ADD COLUMN settings JSON")
        print("Added settings to households")

    # 2. Update products
    c.execute("PRAGMA table_info(products)")
    p_cols = [r[1] for r in c.fetchall()]
    p_additions = [
        ("mercadona_online_id", "VARCHAR(50)"),
        ("enriched_name", "VARCHAR(255)"),
        ("image_url", "TEXT"),
        ("brand", "VARCHAR(100)"),
        ("packaging", "VARCHAR(150)"),
        ("mercadona_url", "TEXT"),
        ("enrichment_status", "VARCHAR(30) DEFAULT 'NONE'"),
        ("enrichment_confidence", "NUMERIC(4, 3)"),
    ]
    for col_name, col_type in p_additions:
        if col_name not in p_cols:
            c.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name} to products")

    # 3. Create mercadona_online_products table if not exists
    c.execute("""
    CREATE TABLE IF NOT EXISTS mercadona_online_products (
        id VARCHAR(50) PRIMARY KEY,
        display_name VARCHAR(255) NOT NULL,
        slug VARCHAR(255) NOT NULL,
        brand VARCHAR(100),
        packaging VARCHAR(150),
        thumbnail_url TEXT NOT NULL,
        share_url TEXT,
        reference_price NUMERIC(10, 3),
        reference_format VARCHAR(20),
        unit_price NUMERIC(10, 2),
        category_path VARCHAR(255),
        warehouse_code VARCHAR(20),
        raw_payload JSON,
        last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS ix_mop_display_name ON mercadona_online_products(display_name)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_mop_brand ON mercadona_online_products(brand)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_mop_warehouse ON mercadona_online_products(warehouse_code)")

    conn.commit()
    print("Database schema successfully updated for Mercadona Online integration!")


if __name__ == "__main__":
    migrate()
