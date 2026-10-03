CREATE TABLE IF NOT EXISTS slots (
    id          SERIAL PRIMARY KEY,
    lot_id      INT NOT NULL DEFAULT 1,
    label       TEXT NOT NULL,
    size_class  SMALLINT NOT NULL CHECK (size_class BETWEEN 1 AND 4),
    status      TEXT NOT NULL DEFAULT 'free' CHECK (status IN ('free', 'occupied', 'reserved')),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (lot_id, label)
);

CREATE TABLE IF NOT EXISTS reservations (
    id            SERIAL PRIMARY KEY,
    slot_id       INT NOT NULL REFERENCES slots(id),
    plate         TEXT NOT NULL,
    vehicle_class SMALLINT NOT NULL CHECK (vehicle_class BETWEEN 1 AND 4),
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','expired','cancelled')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ,
    ended_at      TIMESTAMPTZ
);

-- Speeds up the "smallest free slot that fits" search
CREATE INDEX IF NOT EXISTS idx_slots_lookup ON slots (lot_id, status, size_class, id);
CREATE INDEX IF NOT EXISTS idx_reservations_slot ON reservations (slot_id);

-- One active reservation per slot (safety net against double-booking)
CREATE UNIQUE INDEX IF NOT EXISTS one_active_reservation_per_slot
    ON reservations (slot_id) WHERE status = 'active';
