import json
import pandas as pd

# 1) Загрузить справочники из JSON
with open('units.json', encoding='utf8') as f:
    units = json.load(f)
with open('equipment.json', encoding='utf8') as f:
    equipment = json.load(f)

# 2) Подготовить DataFrame юнитов
unit_rows = []
for key, u in units.items():
    val = u.get('cost', {}).get('value', 0)
    cur = u.get('cost', {}).get('currency', '')
    # разделяем дукаты и очки славы
    if 'очко' in cur:
        duc, glo = 0, val
    else:
        duc, glo = val, 0
    unit_rows.append({
        'UnitKey':    key,
        'UnitName':   u.get('name', ''),
        'BaseDucats': duc,
        'BaseGlory':  glo
    })
units_df = pd.DataFrame(unit_rows)

# 3) Подготовить DataFrame экипировки
equip_rows = []
for cat, items in equipment.items():
    for it in items:
        if 'key' not in it:
            continue
        val = it.get('cost', {}).get('value', 0)
        cur = it.get('cost', {}).get('currency', '')
        if 'очко' in cur:
            duc, glo = 0, val
        else:
            duc, glo = val, 0
        equip_rows.append({
            'EquipKey':   it['key'],
            'EquipName':  it.get('name', ''),
            'CostDucats': duc,
            'CostGlory':  glo
        })
equip_df = pd.DataFrame(equip_rows)

# 4) Создать пустой шаблон Roster
columns = ['Unit', 'Quantity'] + [f'Equip{i}' for i in range(1, 9)] + ['Selected Items', 'TotalDucats']
roster_df = pd.DataFrame(columns=columns)

# 5) Записать всё в Excel
output_file = 'army_full_roster_template.xlsx'
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    units_df.to_excel(writer, sheet_name='Units', index=False)
    equip_df.to_excel(writer, sheet_name='Equipment', index=False)
    roster_df.to_excel(writer, sheet_name='Roster', index=False)

    workbook  = writer.book
    worksheet = writer.sheets['Roster']

    # Диапазоны для списков
    units_range = f"Units!$B$2:$B${len(units_df) + 1}"
    equip_range = f"Equipment!$B$2:$B${len(equip_df) + 1}"

    # Validation: список юнитов в колонке A (A2:A100)
    worksheet.data_validation('A2:A100', {
        'validate': 'list',
        'source': units_range
    })

    # Validation: выбор экипировки в колонках C–J (Equip1…Equip8)
    for col in range(2, 10):  # C=2…J=9
        col_letter = chr(ord('A') + col)
        worksheet.data_validation(f'{col_letter}2:{col_letter}100', {
            'validate': 'list',
            'source': equip_range
        })

    # Формулы для TEXTJOIN и подсчёта TotalDucats
    for row in range(2, 102):
        # TEXTJOIN списка выбранных предметов в колонке K
        equip_cells = [f"{chr(ord('A')+c)}{row}" for c in range(2, 10)]
        join_formula = f"=TEXTJOIN(\", \", TRUE, {','.join(equip_cells)})"
        worksheet.write_formula(f'K{row}', join_formula)

        # TotalDucats в колонке L:
        # =Quantity * (VLOOKUP(Unit) + SUM of VLOOKUP(each Equip))
        unit_cell = f"A{row}"
        qty_cell  = f"B{row}"
        base_lookup = f"IFERROR(VLOOKUP({unit_cell},Units!$B:$D,2,FALSE),0)"
        equip_sum = "+".join(
            f"IFERROR(VLOOKUP({cell},Equipment!$B:$D,3,FALSE),0)"
            for cell in equip_cells
        )
        total_formula = f"={qty_cell}*({base_lookup}+({equip_sum}))"
        worksheet.write_formula(f'L{row}', total_formula)

    # Общая сумма всей команды внизу
    worksheet.write('J104', 'Grand Total:')
    worksheet.write_formula('L104', '=SUM(L2:L101)')

print(f"Шаблон создан: {output_file}")
