import json
import streamlit as st
import re
import os

# Первая команда — конфигурация страницы
st.set_page_config(page_title="Army Builder", layout="wide")

GLORY_LIMIT = 10
CARD_WIDTH = 200  # ширина изображения

# Gothic CSS для рамок
st.markdown("""
<style>
.gothic-card {
  background-color: #1a1a1a;
  border: 3px solid #550000;
  border-radius: 8px;
  padding: 16px;
  margin: 8px;
  color: #f5f0e1;
  font-family: 'Old English Text MT', serif;
}
.gothic-card h2, .gothic-card h3 {
  margin: 4px 0;
  color: #ddbb88;
}
.equip-row {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}
.equip-name {
  flex: 1;
}
.equip-question {
  margin-left: 8px;
  color: #ddbb88;
  cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

st.title("Army Builder")

# Пути к изображениям
IMAGE_MAP = {
    "warProphet":            "prophet.jpg",
    "castigator":            "orthodoxy-officer-final-artstation.jpg",
    "communicant":           "Crusade-Communicant.jpg",
    "communicantATHunter":   "communicant.jpg",
    "ecclesiasticPrisoners": "prisoners.jpg",
    "stigmaticNuns":         "nuns.jpg",
    "shrineAnchorite":       "anchorite.jpg",
    "trenchPilgrim":         "pilgrim.jpg",
    "combatMedic":           "Combat-Medic.jpg",
    "witchburner":           "witch-hunter-general.jpg",
    "mendelistAmmoMonk":     "Ammo-Monk.jpg"
}

# Загрузка данных
with open("units.json", encoding="utf8") as f:
    units = json.load(f)
with open("equipment.json", encoding="utf8") as f:
    equipment = json.load(f)

# Подготовка списка экипировки
all_equips = []
for cat, items in equipment.items():
    for it in items:
        if "key" in it:
            it["_category"] = cat
            all_equips.append(it)
equip_by_key = {it["key"]: it for it in all_equips}

# Маппинг английских имен
english_to_key = {"pistol":"pistol","autogun":"autoPistol","war cross":"battleCross"}

def unit_base_cost(u):
    c = u.get("cost", {})
    return c.get("value", 0), c.get("currency", "дукатов")

def get_allowed_keys(unit, unit_key):
    if unit_key == "ecclesiasticPrisoners":
        return {"tortureDevice"}
    if unit_key == "stigmaticNuns":
        allowed = {"pistol","autoPistol","battleCross"}
        allowed |= {it['key'] for it in all_equips if it['_category']=='meleeWeapons'}
        allowed |= {it['key'] for it in all_equips if it['_category'] in ('armor','equipment')}
        return allowed
    txt = unit.get('allowedEquipment','').lower()
    allowed = set()
    m = re.search(r"дальн\.\s*только\s*([^,;]+)", txt)
    if m:
        for name in [n.strip().lower() for n in m.group(1).split(',')]:
            k = english_to_key.get(name)
            if k: allowed.add(k)
    else:
        allowed |= {it['key'] for it in all_equips if it['_category']=='rangedWeapons'}
    allowed |= {it['key'] for it in all_equips if it['_category']=='meleeWeapons'}
    allowed |= {it['key'] for it in all_equips if it['_category'] in ('armor','equipment')}
    return allowed

# Состояние отряда
if 'roster' not in st.session_state:
    st.session_state.roster = []

def remove_slot(idx):
    st.session_state.roster.pop(idx)

MERC_KEYS=["combatMedic","witchburner","communicantATHunter","mendelistAmmoMonk"]
cols_count=3

def render_card(ukey,u):
    used = sum(1 for s in st.session_state.roster if s['unit_key']==ukey)
    rem = u['max_count'] - used
    if rem<=0: return
    st.markdown('<div class="gothic-card">', unsafe_allow_html=True)
    img = IMAGE_MAP.get(ukey)
    img_col, desc_col = st.columns([1,2])
    with img_col:
        if img and os.path.exists(os.path.join('images',img)):
            st.image(os.path.join('images',img), width=CARD_WIDTH)
    with desc_col:
        st.subheader(u['name'])
        stats = u.get('stats',{})
        if stats:
            st.write(' | '.join(f"{k.upper()}: {v}" for k,v in stats.items()))
        st.write(f"Оружие: {u.get('allowedEquipment','')}")
        kws = u.get('keywords',[])
        if kws:
            st.write('Ключевые слова: ' + ', '.join(kws))
        if 'description' in u:
            st.write(u['description'])
        for ab in u.get('abilities',[]):
            st.markdown(f"**{ab['name']}**: {ab['text']}")
    cnt_col, btn_col, _ = st.columns([1,1,1])
    cnt = cnt_col.number_input('', min_value=0, max_value=rem, value=0, key=f'cnt_{ukey}', label_visibility='collapsed')
    if btn_col.button('Добавить', key=f'add_{ukey}') and cnt>0:
        for _ in range(cnt):
            bv,bc = unit_base_cost(u)
            st.session_state.roster.append({
                'unit_key': ukey,
                'name': u['name'],
                'base_val': bv,
                'base_cur': bc,
                'equip': [],
                'ducats': 0,
                'glory': 0
            })
    st.markdown('</div>', unsafe_allow_html=True)

st.header('1. Выберите персонажей')
row=0
for ukey,u in units.items():
    if ukey in MERC_KEYS: continue
    if row%cols_count==0: cols=st.columns(cols_count)
    with cols[row%cols_count]: render_card(ukey,u)
    row+=1
st.subheader('Наемники')
row=0
for ukey in MERC_KEYS:
    if ukey not in units: continue
    if row%cols_count==0: cols=st.columns(cols_count)
    with cols[row%cols_count]: render_card(ukey,units[ukey])
    row+=1

st.markdown('---')
st.header('2. Экипировка и управление')
for i,slot in enumerate(st.session_state.roster):
    u = units[slot['unit_key']]
    allowed = get_allowed_keys(u, slot['unit_key'])
    with st.expander(slot['name']):
        mc, dc = st.columns([3,1])
        dc.button('❌', key=f'rem_{i}', on_click=remove_slot, args=(i,))
        slot['equip']=[]
        duc = slot['ducats'] = 0
        gl = slot['glory'] = 0
        bv, bc = unit_base_cost(u)
        if bc.startswith('очко'): gl += bv
        else: duc += bv
        for label, cat in [
            ('Дальнобойное','rangedWeapons'),
            ('Ближний бой','meleeWeapons'),
            ('Броня','armor'),
            ('Прочее','equipment')
        ]:
            mc.markdown(f"**{label}**")
            for it in [it for it in all_equips if it['_category']==cat and it['key'] in allowed]:
                key = it['key']
                name = it['name']
                cost_v = it['cost']['value']
                cost_c = it['cost']['currency']
                desc = it.get('effect', it.get('specialRules',''))
                cols = mc.columns([8,1,1])
                chk = cols[0].checkbox(f"{name}/{key} — {cost_v} {cost_c}", key=f'chk_{i}_{key}')
                if cols[1].button('?', key=f'info_{i}_{key}'):
                    cols[2].markdown(
                        f"<div style='background:#333;padding:8px;border-radius:4px;color:#f5f0e1'>{desc}</div>",
                        unsafe_allow_html=True
                    )
                if chk:
                    slot['equip'].append(key)
                    if cost_c.startswith('очко'): gl += cost_v
                    else: duc += cost_v
        slot['ducats'] = duc
        slot['glory'] = gl
        mc.write(f"Всего: {duc} дукатов, {gl} glory")

st.markdown('---')
st.header('3. Итоговый состав армии')
if st.session_state.roster:
    rows=[]; tduc=tgl=0
    for s in st.session_state.roster:
        rows.append({'Юнит': s['name'], 'Ducats': s['ducats'], 'Glory': s['glory']})
        tduc += s['ducats']; tgl += s['glory']
    st.table(rows)
    st.sidebar.metric('Всего дукатов', f"{tduc}")
    st.sidebar.metric('Всего glory',  f"{tgl}/{GLORY_LIMIT}")
