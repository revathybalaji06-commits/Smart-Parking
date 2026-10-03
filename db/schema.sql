CREATE TABLE slots(
    id SERIAL PRIMARY KEY,
    lot_id INT NOT NULL DEFAULT 1,
    label TEXT NOT NULL,
    size_class  SMALLINT NOT NULL CHECK (size_class BETWEEN 1 AND 4),
    status TEXT NOT NULL DEFAULT 'free' CHECK (status IN ('free', 'occupied', 'reserved')),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE reservations (
    id            SERIAL PRIMARY KEY,
    slot_id       INT NOT NULL REFERENCES slots(id),
    plate         TEXT NOT NULL,
    vehicle_class SMALLINT NOT NULL CHECK (vehicle_class BETWEEN 1 AND 4),
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','expired','cancelled')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ,
    ended_at      TIMESTAMPTZ
);


-- One active reservation per slot (safety net against double-booking)
CREATE UNIQUE INDEX one_active_reservation_per_slot
    ON reservations (slot_id) WHERE status = 'active';
