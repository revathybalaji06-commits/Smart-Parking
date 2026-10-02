INSERT INTO slots (label, size_class)
SELECT 'C' || g, 1 FROM generate_series(1,10) g
UNION ALL SELECT 'S' || g, 2 FROM generate_series(1,20) g
UNION ALL SELECT 'U' || g, 3 FROM generate_series(1,12) g
UNION ALL SELECT 'F' || g, 4 FROM generate_series(1,8) g;
