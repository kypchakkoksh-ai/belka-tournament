import streamlit as st
import pandas as pd
import gspread
import time

# Настройка страницы
st.set_page_config(page_title="Лига Белки 8 игроков", layout="wide", page_icon="🏆")

# --- СТИЛИЗАЦИЯ И ИНТЕРФЕЙС (Контрастный Желтый для вкладок) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0b3017;
        background-image: radial-gradient(circle, #0e4220 0%, #071f0e 100%);
        color: #f0f2f6;
    }
    .stWidgetFormLabel, label, [data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    /* Контрастная желтая кнопка сохранения */
    div.stForm stButton > button, div.stButton > button:contains("СОХРАНИТЬ") {
        width: 100% !important;
        background-color: #ffcc00 !important;
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 17px !important;
        border-radius: 8px !important;
        border: 2px solid #ffee55 !important;
        padding: 0.6rem 1rem !important;
    }
    div.stForm stButton > button:hover, div.stButton > button:contains("СОХРАНИТЬ"):hover { 
        background-color: #e6b800 !important; 
        color: #000000 !important;
    }
    
    /* Зеленые кнопки действий */
    div.stButton > button {
        background-color: #1e7e34 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    /* Красные кнопки удаления */
    button:contains("УДАЛИТЬ") {
        background-color: #b21f2d !important;
        color: #ffffff !important;
        border: 2px solid #dc3545 !important;
    }
    
    /* СТИЛИЗАЦИЯ ВКЛАДОК: Неактивные - Желтые, Активные - Белые */
    button[data-baseweb="tab"] { 
        font-size: 15px !important; 
        font-weight: bold !important; 
        color: #e2b13c !important; /* Мягкий золотисто-желтый для неактивных */
    }
    button[aria-selected="true"] { 
        color: #ffffff !important; /* Белый для активной вкладки */
        border-bottom-color: #ffcc00 !important; 
    }
    hr { border-top: 1px solid #1e7e34 !important; }
    </style>
""", unsafe_allow_html=True)

# Инициализация подключения через gspread
@st.cache_resource
def get_gspread_client():
    try:
        credentials = dict(st.secrets["gcp_service_account"])
        if "private_key" in credentials:
            credentials["private_key"] = credentials["private_key"].replace("\\n", "\n")
        gc = gspread.service_account_from_dict(credentials)
        return gc
    except Exception as e:
        st.error(f"Ошибка авторизации Google Sheets: {e}")
        return None

gc = get_gspread_client()

# Список твоих 8 участников
DEFAULT_PLAYERS = ["Азирхан", "Аманат", "Данияр", "Елдар", "Мерхат", "Рустем", "Талгат", "Шынгыс"]

@st.cache_data(ttl=2)
def load_data_from_sheets():
    if gc is None:
        return DEFAULT_PLAYERS.copy(), []
    try:
        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
        
        # Загрузка списка игроков
        try:
            worksheet_p = sh.worksheet("players")
            players = [x for x in worksheet_p.col_values(1) if x and x != 'Имя'][:8]
            while len(players) < 8:
                players.append(DEFAULT_PLAYERS[len(players)])
        except:
            players = DEFAULT_PLAYERS.copy()
            
        # Загрузка матчей
        try:
            worksheet_g = sh.worksheet("games")
            all_records = worksheet_g.get_all_records()
            df_g = pd.DataFrame(all_records)
            games = df_g.to_dict(orient='records') if not df_g.empty else []
        except Exception as e:
            st.warning(f"Не удалось загрузить историю игр (возможно, таблица пуста): {e}")
            games = []
            
        for g in games:
            if isinstance(g.get('win_team'), str):
                g['win_team'] = [x.strip() for x in g['win_team'].split(',')]
            if isinstance(g.get('loss_team'), str):
                g['loss_team'] = [x.strip() for x in g['loss_team'].split(',')]
        return players, games
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return DEFAULT_PLAYERS.copy(), []

# Загрузка актуальных данных
players, games = load_data_from_sheets()
st.session_state.players = players
st.session_state.games = games

# --- СИСТЕМА НАЧИСЛЕНИЯ ОЧКОВ (ЛИГА) ---
POINTS_DICT = {
    "Сокыр (12 очков)": 12,
    "Партия (3 очка)": 3,
    "Голый (2 очка)": 2
}

def calculate_match_points(status, eggs):
    base_points = POINTS_DICT[status]
    return (base_points + 1, 0) if eggs else (base_points, 0)

# Матрица расписания (индексы игроков 0-7)
SCHEDULE_INDEXES = [
    {"tour": 1, "m1_w": [0, 1], "m1_l": [2, 3], "m2_w": [4, 5], "m2_l": [6, 7]},
    {"tour": 2, "m1_w": [0, 2], "m1_l": [5, 7], "m2_w": [1, 3], "m2_l": [4, 6]},
    {"tour": 3, "m1_w": [0, 7], "m1_l": [1, 6], "m2_w": [2, 5], "m2_l": [3, 4]},
    {"tour": 4, "m1_w": [0, 6], "m1_l": [2, 4], "m2_w": [1, 7], "m2_l": [3, 5]},
    {"tour": 5, "m1_w": [0, 4], "m1_l": [3, 7], "m2_w": [1, 5], "m2_l": [2, 6]},
    {"tour": 6, "m1_w": [0, 3], "m1_l": [5, 6], "m2_w": [1, 2], "m2_l": [4, 7]},
    {"tour": 7, "m1_w": [0, 5], "m1_l": [1, 4], "m2_w": [3, 6], "m2_l": [2, 7]},
    {"tour": 8, "m1_w": [0, 1], "m1_l": [4, 7], "m2_w": [2, 3], "m2_l": [5, 6]},
    {"tour": 9, "m1_w": [0, 2], "m1_l": [3, 6], "m2_w": [1, 5], "m2_l": [4, 7]},
    {"tour": 10, "m1_w": [0, 7], "m1_l": [2, 6], "m2_w": [1, 3], "m2_l": [5, 4]},
    {"tour": 11, "m1_w": [0, 6], "m1_l": [1, 2], "m2_w": [3, 7], "m2_l": [4, 5]},
    {"tour": 12, "m1_w": [0, 4], "m1_l": [1, 7], "m2_w": [2, 5], "m2_l": [3, 6]},
    {"tour": 13, "m1_w": [0, 3], "m1_l": [2, 4], "m2_w": [1, 6], "m2_l": [5, 7]},
    {"tour": 14, "m1_w": [0, 5], "m1_l": [3, 4], "m2_w": [1, 4], "m2_l": [2, 7]}
]

# --- РАСЧЕТ СТАТИСТИКИ ---
stats = {p: {
    "Очки": 0, "Игры": 0, "Победы": 0, "Поражения": 0, "Средний балл": 0.0,
    "Забитые глаза": 0, "Пропущенные глаза": 0, "Разница глаз": 0,
    "Выигр. Теке": 0, "Проигр. Теке": 0, "Разница Теке": 0,
    "Выигр. Голый": 0, "Проигр. Голый": 0, "Разница Голый": 0,
    "Повесили Яйца": 0, "Получили Яйца": 0, "Разница Яйца": 0,
    "Выигр. Сокыр": 0, "Проигр. Сокыр": 0, "Разница Сокыр": 0,
    "Выигр. Партия": 0, "Проигр. Партия": 0
} for p in st.session_state.players}

pairs_stats = {}

for game in st.session_state.games:
    try:
        w_team = game.get("win_team", [])
        l_team = game.get("loss_team", [])
        if len(w_team) < 2 or len(l_team) < 2: continue
        
        win_pts = int(game.get("win_points", 0))
        loss_pts = int(game.get("loss_points", 0))
        
        # Получаем глаза
        win_eyes = int(game.get("win_eyes", 12))
        loss_eyes = int(game.get("loss_eyes", 0))

        # --- Статистика связок ---
        win_pair = tuple(sorted(w_team))
        loss_pair = tuple(sorted(l_team))

        for pair, pts, is_win, eyes_scored, eyes_conceded in [
            (win_pair, win_pts, True, win_eyes, loss_eyes), 
            (loss_pair, loss_pts, False, loss_eyes, win_eyes)
        ]:
            if pair not in pairs_stats:
                pairs_stats[pair] = {
                    "Очки": 0, "Игры": 0, "Победы": 0,
                    "Забитые глаза": 0, "Пропущенные глаза": 0,
                    "Выигр. Теке": 0, "Проигр. Теке": 0,
                    "Выигр. Голый": 0, "Проигр. Голый": 0,
                    "Повесили Яйца": 0, "Получили Яйца": 0,
                    "Выигр. Сокыр": 0, "Проигр. Сокыр": 0
                }
            pairs_stats[pair]["Очки"] += pts
            pairs_stats[pair]["Игры"] += 1
            pairs_stats[pair]["Забитые глаза"] += eyes_scored
            pairs_stats[pair]["Пропущенные глаза"] += eyes_conceded
            if is_win:
                pairs_stats[pair]["Победы"] += 1

        # --- Личная детализация ---
        raw_status = str(game.get("raw_status", ""))
        is_eggs = str(game.get("eggs_happened", "")).upper() in ["TRUE", "1", "ИСТИНА"]

        # Победители
        for p in w_team:
            if p in stats:
                stats[p]["Очки"] += win_pts
                stats[p]["Игры"] += 1
                stats[p]["Победы"] += 1
                stats[p]["Забитые глаза"] += win_eyes
                stats[p]["Пропущенные глаза"] += loss_eyes
                if "Сокыр" in raw_status:
                    stats[p]["Выигр. Сокыр"] += 1
                    pairs_stats[win_pair]["Выигр. Сокыр"] += 1
                elif "Партия" in raw_status:
                    stats[p]["Выигр. Партия"] += 1
                elif "Голый" in raw_status:
                    stats[p]["Выигр. Голый"] += 1
                    pairs_stats[win_pair]["Выигр. Голый"] += 1
                elif "Теке" in raw_status:
                    stats[p]["Выигр. Теке"] += 1
                    pairs_stats[win_pair]["Выигр. Теке"] += 1
                if is_eggs:
                    stats[p]["Повесили Яйца"] += 1
                    pairs_stats[win_pair]["Повесили Яйца"] += 1
                
        # Проигравшие
        for p in l_team:
            if p in stats:
                stats[p]["Очки"] += loss_pts
                stats[p]["Игры"] += 1
                stats[p]["Поражения"] += 1
                stats[p]["Забитые глаза"] += loss_eyes
                stats[p]["Пропущенные глаза"] += win_eyes
                if "Сокыр" in raw_status:
                    stats[p]["Проигр. Сокыр"] += 1
                    pairs_stats[loss_pair]["Проигр. Сокыр"] += 1
                elif "Партия" in raw_status:
                    stats[p]["Проигр. Партия"] += 1
                elif "Голый" in raw_status:
                    stats[p]["Проигр. Голый"] += 1
                    pairs_stats[loss_pair]["Проигр. Голый"] += 1
                elif "Теке" in raw_status:
                    stats[p]["Проигр. Теке"] += 1
                    pairs_stats[loss_pair]["Проигр. Теке"] += 1
                if is_eggs:
                    stats[p]["Получили Яйца"] += 1
                    pairs_stats[loss_pair]["Получили Яйца"] += 1
    except:
        continue

# Расчет разниц по игрокам
for p in stats:
    if stats[p]["Игры"] > 0:
        stats[p]["Средний балл"] = round(stats[p]["Очки"] / stats[p]["Игры"], 2)
    stats[p]["Разница глаз"] = stats[p]["Забитые глаза"] - stats[p]["Пропущенные глаза"]
    stats[p]["Разница Теке"] = stats[p]["Выигр. Теке"] - stats[p]["Проигр. Теке"]
    stats[p]["Разница Голый"] = stats[p]["Выигр. Голый"] - stats[p]["Проигр. Голый"]
    stats[p]["Разница Яйца"] = stats[p]["Повесили Яйца"] - stats[p]["Получили Яйца"]
    stats[p]["Разница Сокыр"] = stats[p]["Выигр. Сокыр"] - stats[p]["Проигр. Сокыр"]

df_leaderboard = pd.DataFrame.from_dict(stats, orient='index').reset_index()
df_leaderboard.columns = [
    "Игрок", "Всего очков", "Сыграно игр", "Победы", "Поражения", "Средний балл",
    "Забитые глаза", "Пропущенные глаза", "Разница глаз",
    "Выигр. Теке", "Проигр. Теке", "Разница Теке",
    "Выигр. Голый", "Проигр. Голый", "Разница Голый",
    "Повесили Яйца", "Получили Яйца", "Разница Яйца",
    "Выигр. Сокыр", "Проигр. Сокыр", "Разница Сокыр",
    "Выигр. Партия", "Проигр. Партия"
]

# === ЭЛЕМЕНТЫ ИНТЕРФЕЙСА ===
st.title("🏆 КЛАССИЧЕСКАЯ ЛИГА БЕЛКИ (8 ИГРОКОВ)")

if st.button("🔄 Обновить общую таблицу"):
    st.cache_data.clear()
    st.rerun()

st.markdown("### 📊 Главная турнирная таблица")

main_table_cols = [
    "Игрок", "Всего очков", "Сыграно игр", "Средний балл",
    "Забитые глаза", "Пропущенные глаза", "Разница глаз",
    "Выигр. Теке", "Проигр. Теке", "Разница Теке",
    "Выигр. Голый", "Проигр. Голый", "Разница Голый",
    "Повесили Яйца", "Получили Яйца", "Разница Яйца",
    "Выигр. Сокыр", "Проигр. Сокыр", "Разница Сокыр"
]

# ИСПРАВЛЕНИЕ БАГА: Сначала сортируем весь DataFrame (где есть колонка "Победы"), а потом выбираем отображаемые колонки
df_main = df_leaderboard.sort_values(
    by=["Всего очков", "Победы", "Разница глаз", "Средний балл"], 
    ascending=[False, False, False, False]
)[main_table_cols].reset_index(drop=True)

df_main.index = df_main.index + 1
st.dataframe(df_main, use_container_width=True)

st.markdown("---")

# ГЛОБАЛЬНЫЕ ВКЛАДКИ
tab_sched, tab_leader, tab_positive, tab_negative, tab_pairs, tab_history = st.tabs([
    "📅 Расписание туров", "🏆 Главная таблица", "🚀 Раздали (Выигрыши)", "📉 Словленные (Проигрыши)", "👥 Рейтинг связок", "📝 История игр"
])

# 1. РАСПИСАНИЕ ТУРОВ
with tab_sched:
    st.markdown("#### Календарь матчей Лиги")
    sched_data = []
    for s in SCHEDULE_INDEXES:
        p_names = st.session_state.players
        sched_data.append({
            "Тур": f"Тур {s['tour']}",
            "Матч 1": f"{p_names[s['m1_w'][0]]} + {p_names[s['m1_w'][1]]}  🆚  {p_names[s['m1_l'][0]]} + {p_names[s['m1_l'][1]]}",
            "Матч 2": f"{p_names[s['m2_w'][0]]} + {p_names[s['m2_w'][1]]}  🆚  {p_names[s['m2_l'][0]]} + {p_names[s['m2_l'][1]]}"
        })
    st.dataframe(pd.DataFrame(sched_data), use_container_width=True, hide_index=True)

# 2. ГЛАВНАЯ ТАБЛИЦА
with tab_leader:
    st.dataframe(df_main, use_container_width=True)

# 3. ВЫИГРЫШИ
with tab_positive:
    sub_pos_tabs = st.tabs([
        "🐐 Теке", "📊 Разница Теке", 
        "🪵 Голый", "📊 Разница Голого", 
        "🥚 Повесили Яйца", "📊 Разница Яиц", 
        "👁️ Сокыр", "📊 Разница Сокыра",
        "👁️ Забитые Глаза", "📊 Разница Глаз"
    ])
    
    with sub_pos_tabs[0]:
        df_view = df_leaderboard[["Игрок", "Выигр. Теке"]].sort_values(by="Выигр. Теке", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[1]:
        df_view = df_leaderboard[["Игрок", "Разница Теке"]].sort_values(by="Разница Теке", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[2]:
        df_view = df_leaderboard[["Игрок", "Выигр. Голый"]].sort_values(by="Выигр. Голый", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[3]:
        df_view = df_leaderboard[["Игрок", "Разница Голый"]].sort_values(by="Разница Голый", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[4]:
        df_view = df_leaderboard[["Игрок", "Повесили Яйца"]].sort_values(by="Повесили Яйца", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[5]:
        df_view = df_leaderboard[["Игрок", "Разница Яйца"]].sort_values(by="Разница Яйца", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[6]:
        df_view = df_leaderboard[["Игрок", "Выигр. Сокыр"]].sort_values(by="Выигр. Сокыр", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[7]:
        df_view = df_leaderboard[["Игрок", "Разница Сокыр"]].sort_values(by="Разница Сокыр", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[8]:
        df_view = df_leaderboard[["Игрок", "Забитые глаза"]].sort_values(by="Забитые глаза", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_pos_tabs[9]:
        df_view = df_leaderboard[["Игрок", "Разница глаз"]].sort_values(by="Разница глаз", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)

# 4. ПРОИГРЫШИ
with tab_negative:
    sub_neg_tabs = st.tabs([
        "🐐 Проигр. Теке", "📊 Разница Теке", 
        "🪵 Проигр. Голый", "📊 Разница Голого", 
        "🥚 Получили Яйца", "📊 Разница Яиц", 
        "👁️ Проигр. Сокыр", "📊 Разница Сокыра",
        "👁️ Пропущенные Глаза", "📊 Разница Глаз"
    ])
    
    with sub_neg_tabs[0]:
        df_view = df_leaderboard[["Игрок", "Проигр. Теке"]].sort_values(by="Проигр. Теке", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[1]:
        df_view = df_leaderboard[["Игрок", "Разница Теке"]].sort_values(by="Разница Теке", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[2]:
        df_view = df_leaderboard[["Игрок", "Проигр. Голый"]].sort_values(by="Проигр. Голый", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[3]:
        df_view = df_leaderboard[["Игрок", "Разница Голый"]].sort_values(by="Разница Голый", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[4]:
        df_view = df_leaderboard[["Игрок", "Получили Яйца"]].sort_values(by="Получили Яйца", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[5]:
        df_view = df_leaderboard[["Игрок", "Разница Яйца"]].sort_values(by="Разница Яйца", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[6]:
        df_view = df_leaderboard[["Игрок", "Проигр. Сокыр"]].sort_values(by="Проигр. Сокыр", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[7]:
        df_view = df_leaderboard[["Игрок", "Разница Сокыр"]].sort_values(by="Разница Сокыр", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[8]:
        df_view = df_leaderboard[["Игрок", "Пропущенные глаза"]].sort_values(by="Пропущенные глаза", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)
    with sub_neg_tabs[9]:
        df_view = df_leaderboard[["Игрок", "Разница глаз"]].sort_values(by="Разница глаз", ascending=False).reset_index(drop=True)
        df_view.index = df_view.index + 1
        st.dataframe(df_view, use_container_width=True)

# 5. РЕЙТИНГ СВЯЗОК
with tab_pairs:
    if pairs_stats:
        p_list = []
        for k, v in pairs_stats.items():
            diff_teke = v["Выигр. Теке"] - v["Проигр. Теке"]
            diff_goly = v["Выигр. Голый"] - v["Проигр. Голый"]
            diff_eggs = v["Повесили Яйца"] - v["Получили Яйца"]
            diff_sokyr = v["Выигр. Сокыр"] - v["Проигр. Сокыр"]
            diff_eyes = v["Забитые глаза"] - v["Пропущенные глаза"]
            p_list.append({
                "Пара игроков": f"{k[0]} 🤝 {k[1]}",
                "Очки": v["Очки"],
                "Игры": v["Игры"],
                "Победы": v["Победы"],
                "Средний балл": round(v["Очки"] / v["Игры"] if v["Игры"] > 0 else 0, 2),
                "Забитые глаза": v["Забитые глаза"],
                "Пропущенные глаза": v["Пропущенные глаза"],
                "Разница глаз": diff_eyes,
                "Разница Теке": diff_teke,
                "Разница Голый": diff_goly,
                "Разница Яйца": diff_eggs,
                "Разница Сокыр": diff_sokyr
            })
        df_pairs_all = pd.DataFrame(p_list)

        sub_pair_tabs = st.tabs([
            "📊 2.1. Средний балл", 
            "📈 2.2. Набранные очки", 
            "🐐 2.3. Лучшая разница Теке / Голый", 
            "🥚 2.4. Лучшая разница Яиц", 
            "👁️ 2.5. Лучшая разница Сокыра",
            "👁️ 2.6. Лучшая разница по Глазам"
        ])

        with sub_pair_tabs[0]:
            df_p_view = df_pairs_all[["Пара игроков", "Средний балл", "Игры"]].sort_values(by="Средний балл", ascending=False).reset_index(drop=True)
            df_p_view.index = df_p_view.index + 1
            st.dataframe(df_p_view, use_container_width=True)
        with sub_pair_tabs[1]:
            df_p_view = df_pairs_all[["Пара игроков", "Очки", "Игры"]].sort_values(by="Очки", ascending=False).reset_index(drop=True)
            df_p_view.index = df_p_view.index + 1
            st.dataframe(df_p_view, use_container_width=True)
        with sub_pair_tabs[2]:
            df_p_view = df_pairs_all[["Пара игроков", "Разница Теке", "Разница Голый", "Игры"]].sort_values(by=["Разница Теке", "Разница Голый"], ascending=False).reset_index(drop=True)
            df_p_view.index = df_p_view.index + 1
            st.dataframe(df_p_view, use_container_width=True)
        with sub_pair_tabs[3]:
            df_p_view = df_pairs_all[["Пара игроков", "Разница Яйца", "Игры"]].sort_values(by="Разница Яйца", ascending=False).reset_index(drop=True)
            df_p_view.index = df_p_view.index + 1
            st.dataframe(df_p_view, use_container_width=True)
        with sub_pair_tabs[4]:
            df_p_view = df_pairs_all[["Пара игроков", "Разница Сокыр", "Игры"]].sort_values(by="Разница Сокыр", ascending=False).reset_index(drop=True)
            df_p_view.index = df_p_view.index + 1
            st.dataframe(df_p_view, use_container_width=True)
        with sub_pair_tabs[5]:
            df_p_view = df_pairs_all[["Пара игроков", "Разница глаз", "Забитые глаза", "Пропущенные глаза", "Игры"]].sort_values(by="Разница глаз", ascending=False).reset_index(drop=True)
            df_p_view.index = df_p_view.index + 1
            st.dataframe(df_p_view, use_container_width=True)
    else:
        st.info("Статистики парных сыгранных матчей пока нет.")

# 6. ИСТОРИЯ ИГР
with tab_history:
    if st.session_state.games:
        log_data = []
        for i, g in enumerate(st.session_state.games, 1):
            w_eyes = g.get("win_eyes", 12)
            l_eyes = g.get("loss_eyes", 0)
            log_data.append({
                "Матч №": i, 
                "Победители": f"{g['win_team'][0]}, {g['win_team'][1]}", 
                "Проигравшие": f"{g['loss_team'][0]}, {g['loss_team'][1]}", 
                "Счет по глазам": f"{w_eyes} : {l_eyes}",
                "Статус": g.get("status"), 
                "Очки победителям": f"+{g['win_points']}"
            })
        st.dataframe(pd.DataFrame(log_data)[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("В этой Лиге еще нет сыгранных матчей.")

st.markdown("---")

# --- ОРГАНЫ УПРАВЛЕНИЯ И СОХРАНЕНИЯ ---
col_bottom1, col_bottom2 = st.columns([1, 1])

with col_bottom1:
    st.markdown("### ➕ Регистрация игры")
    match_password = st.text_input("🔑 Пароль администратора:", type="password")

    with st.form("match_form", clear_on_submit=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p1 = st.selectbox("Победитель 1", st.session_state.players, index=0)
            p3 = st.selectbox("Проигравший 1", st.session_state.players, index=2)
        with col_p2:
            p2 = st.selectbox("Победитель 2", st.session_state.players, index=1)
            p4 = st.selectbox("Проигравший 2", st.session_state.players, index=3)
        
        st.markdown("---")
        
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            win_eyes_input = st.number_input("Глаза Победителей (всегда 12)", min_value=12, max_value=12, value=12, step=1)
        with col_e2:
            loss_eyes_input = st.number_input("Глаза Проигравших (0-11)", min_value=0, max_value=11, value=4, step=1)
            
        status = st.selectbox("Что дали?", list(POINTS_DICT.keys()))
        eggs = st.checkbox("Повесили «Яйца» (+1 очко победителю)")
        
        if st.form_submit_button("СОХРАНИТЬ РЕЗУЛЬТАТ"):
            if match_password != "6666":
                st.error("🔒 Неверный пароль!")
            elif len({p1, p2, p3, p4}) < 4:
                st.error("Ошибка: Игроки дублируются в матче!")
            elif gc is None:
                st.error("Ошибка подключения к Google Таблицам.")
            else:
                win_pts, loss_pts = calculate_match_points(status, eggs)
                try:
                    sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                    worksheet_g = sh.worksheet("games")
                    
                    worksheet_g.append_row([
                        f"{p1}, {p2}",               # win_team
                        f"{p3}, {p4}",               # loss_team
                        int(win_pts),                # win_points
                        int(loss_pts),               # loss_points
                        str(status),                 # status
                        str(eggs).upper(),           # eggs_happened
                        f"{status} {'+ Яйца' if eggs else ''}", # status_full
                        float(time.time()),          # timestamp
                        int(win_eyes_input),         # win_eyes
                        int(loss_eyes_input)         # loss_eyes
                    ])
                    st.success("Результат матча сохранен в Google Таблицу!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка сохранения: {e}")

    st.markdown("### 🛠️ Корректировка результатов")
    with st.expander("❌ Удалить конкретную игру по номеру", expanded=False):
        if st.session_state.games:
            game_numbers = list(range(1, len(st.session_state.games) + 1))
            selected_game_num = st.selectbox("Выберите номер матча для удаления:", game_numbers)
            
            g_idx = selected_game_num - 1
            game_info = st.session_state.games[g_idx]
            st.info(f"**Матч №{selected_game_num}:** Победители: {', '.join(game_info['win_team'])} | Проигравшие: {', '.join(game_info['loss_team'])} | Статус: {game_info.get('status')}")
            
            if st.button("УДАЛИТЬ ВЫБРАННЫЙ МАТЧ"):
                if match_password != "6666":
                    st.error("🔒 Введите пароль администратора!")
                elif gc is None:
                    st.error("Нет подключения к Google Таблицам.")
                else:
                    try:
                        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                        worksheet_g = sh.worksheet("games")
                        row_to_delete = selected_game_num + 1
                        worksheet_g.delete_rows(row_to_delete)
                        
                        st.success(f"Матч №{selected_game_num} успешно удален!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка удаления: {e}")
        else:
            st.info("База матчей пуста.")

with col_bottom2:
    st.markdown("### ⚙️ Участники Лиги")
    st.info("Состав Лиги зафиксирован на 8 участников.")
    st.dataframe(pd.DataFrame(st.session_state.players, columns=["Имя участника"]), use_container_width=True)
