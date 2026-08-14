-- Cash articles (income/expense) and day ledger like Service CRM

CREATE TABLE IF NOT EXISTS cash_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    kind VARCHAR(20) NOT NULL CHECK (kind IN ('income', 'expense')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cash_transactions (
    id SERIAL PRIMARY KEY,
    amount_cents INTEGER NOT NULL,
    kind VARCHAR(20) NOT NULL CHECK (kind IN ('income', 'expense')),
    method VARCHAR(20) NOT NULL DEFAULT 'cash',
    category_id INTEGER REFERENCES cash_categories(id) ON DELETE SET NULL,
    member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    payment_id INTEGER REFERENCES payments(id) ON DELETE SET NULL,
    cash_shift_id INTEGER REFERENCES cash_shifts(id) ON DELETE SET NULL,
    paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cash_tx_paid ON cash_transactions (paid_at);
CREATE INDEX IF NOT EXISTS idx_cash_tx_kind ON cash_transactions (kind);

INSERT INTO cash_categories (name, kind)
SELECT v.name, v.kind
FROM (VALUES
    ('Абонемент', 'income'),
    ('Гостевой визит', 'income'),
    ('PT', 'income'),
    ('Прочий приход', 'income'),
    ('Зарплата', 'expense'),
    ('Закупка', 'expense'),
    ('Прочий расход', 'expense')
) AS v(name, kind)
WHERE NOT EXISTS (
    SELECT 1 FROM cash_categories c WHERE c.name = v.name AND c.kind = v.kind
);
