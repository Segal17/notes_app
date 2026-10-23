-- Удаляем из seed_inventory колонки, которые теперь в cultures
ALTER TABLE seed_inventory
  DROP COLUMN IF EXISTS expiry_text,
  DROP COLUMN IF EXISTS need,
  DROP COLUMN IF EXISTS need_unit,
  DROP COLUMN IF EXISTS coefficient;

-- Комментарии к оставшимся колонкам (на случай, если не было)
COMMENT ON COLUMN seed_inventory.quantity      IS 'Остаток — сколько семян есть (число)';
COMMENT ON COLUMN seed_inventory.quantity_unit IS 'Единица остатка: г, шт, кг';
