import streamlit as st
import pandas as pd
import gspread
import time
import itertools

# Настройка страницы
st.set_page_config(page_title="Лига Белки", layout="wide", page_icon="🏆")

# --- СТИЛИЗАЦИЯ И ИНТЕРФЕЙС ---
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
    
    div.stForm stButton > button, div.stForm stButton > button:contains("СОХРАНИТЬ") {
        width: 100% !important;
        background-color: #ffcc00 !important;
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 17px !important;
        border-radius: 8px !important;
        border: 2px solid #ffee55 !important;
        padding: 0.6rem 1rem !important;
    }
    div.stForm stButton > button:hover, div.stForm stButton > button:contains("СОХРАНИТЬ"):hover { 
        background-color: #e6b800 !important; 
        color: #000000 !important;
    }
    
    div.stButton > button {
        background-color: #1e7e34 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    button:contains("УДАЛИТЬ"), button:contains("Исключить"), button:contains("СБРОСИТЬ") {
        background-color: #b21f2d !important;
        color: #ffffff !important;
        border: 2px solid #dc3545 !important;
        font-weight: bold !important;
    }
    
    button[data-baseweb="tab"] { 
        font-size: 15px !important; 
        font-weight: bold !important; 
        color: #e2b13c !important;
    }
    button[aria-selected="true"] { 
        color: #ffffff !important; 
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

DEFAULT_PLAYERS = ["Азирхан", "Аманат", "Данияр", "Елдар", "Мерхат", "Рустем", "Талгат", "Шынгыс", "Марат", "Ерлан"]

def load_fresh_data():
    if gc is None:
        return DEFAULT_PLAYERS.copy(), []
    try:
        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
        try:
            worksheet_p = sh.worksheet("players")
            players = [x for x in worksheet_p.col_values(1) if x and x != 'Имя']
            if players and "Ерлан" not in players:
                worksheet_p.append_row(["Ерлан"])
                players.append("Ерлан")
            if not players:
                players = DEFAULT_PLAYERS.copy()
        except:
            players = DEFAULT_PLAYERS.copy()
            
        try:
            worksheet_g = sh.worksheet("games")
            all_records = worksheet_g.get_all_records()
            df_g = pd.DataFrame(all_records)
            games = df_g.to_dict(orient='records') if not df_g.empty else []
        except:
            games = []
            
        for g in games:
            if isinstance(g.get('win_team'), str):
                g['win_team'] = [x.strip() for x in g['win_team'].split(',')]
            if isinstance(g.get('loss_team'), str):
                g['loss_team'] = [x.strip() for x in g['loss_team'].split(',')]
        return players, games
    except Exception as e:
        st.error(f"Ошибка сети при получении данных: {e}")
        return DEFAULT_PLAYERS.copy(), []

if "data_loaded" not in st.session_state or st.sidebar.button("🔄 Сбросить кэш приложения"):
    p_fresh, g_fresh = load_fresh_data()
    st.session_state.players = p_fresh
    st.session_state.games = g_fresh
    st.session_state.data_loaded = True

def force_reload():
    p_fresh, g_fresh = load_fresh_data()
    st.session_state.players = p_fresh
    st.session_state.games = g_fresh
    st.rerun()

POINTS_DICT = {
    "Партия (3 очка)": 3,
    "Голый (3 очка)": 3,
    "Сокыр (12 очков)": 12
}

def calculate_match_points(status, eggs):
    base_points = POINTS_DICT[status]
    return (base_points + 1, 0) if eggs else (base_points, 0)


# --- РАСПРЕДЕЛЕНИЕ 630 МАТЧЕЙ НА 10 СБАЛАНСИРОВАННЫХ ЭТАПОВ ---
@st.cache_data
def generate_perfect_10_stages_schedule(player_list):
    if len(player_list) != 10:
        return []

    # Генерируем полный пул из 630 уникальных матчей
    all_pairs = list(itertools.combinations(player_list, 2))
    unique_matches = []
    for i, p1 in enumerate(all_pairs):
        for p2 in all_pairs[i+1:]:
            if set(p1).isdisjoint(set(p2)):
                unique_matches.append((frozenset(p1), frozenset(p2)))

    schedule = []
    match_pool = list(unique_matches)
    
    # Распределяем по 63 матча на этап (10 этапов)
    for stage in range(1, 11):
        stage_matches_count = 0
        tour = 1
        
        while stage_matches_count < 63 and match_pool:
            # Организуем пропуски туров для баланса текущей игровой сессии
            shifted = player_list[(stage + tour) % 10:] + player_list[:(stage + tour) % 10]
            bp1, bp2 = shifted[0], shifted[1]
            active_players = set(player_list) - {bp1, bp2}
            
            m1_found, m2_found = None, None
            
            # Ищем первый матч для тура
            for idx, match in enumerate(match_pool):
                if (match[0] | match[1]).issubset(active_players):
                    m1_found = match
                    match_pool.pop(idx)
                    stage_matches_count += 1
                    break
            
            # Ищем второй матч для тура, если лимит этапа (63) еще не достигнут
            if m1_found and stage_matches_count < 63:
                remaining_active = active_players - (m1_found[0] | m1_found[1])
                for idx, match in enumerate(match_pool):
                    if (match[0] | match[1]) == remaining_active:
                        m2_found = match
                        match_pool.pop(idx)
                        stage_matches_count += 1
                        break
            
            # Формируем текстовый вывод
            m1_p1 = tuple(m1_found[0]) if m1_found else ("—", "—")
            m1_p2 = tuple(m1_found[1]) if m1_found else ("—", "—")
            m2_p1 = tuple(m2_found[0]) if m2_found else ("—", "—")
            m2_p2 = tuple(m2_found[1]) if m2_found else ("—", "—")
            
            if m1_found or m2_found:
                schedule.append({
                    "stage": stage,
                    "tour": tour,
                    "bypass": f"{bp1}, {bp2}" if m2_found else f"Финальный стык этапа",
                    "m1_p1": m1_p1, "m1_p2": m1_p2,
                    "m2_p1": m2_p1, "m2_p2": m2_p2
                })
                tour += 1
            else:
                # Если игры заблокированы составом, берем любой доступный матч из пула
                if match_pool:
                    wild_match = match_pool.pop(0)
                    stage_matches_count += 1
                    schedule.append({
                        "stage": stage,
                        "tour": tour,
                        "bypass": "Свободная ротация",
                        "m1_p1": tuple(wild_match[0]), "m1_p2": tuple(wild_match[1]),
                        "m2_p1": ("—", "—"), "m2_p2": ("—", "—")
                    })
                    tour += 1
                else:
                    break
                    
    return schedule

DYNAMIC_SCHEDULE = generate_perfect_10_stages_schedule(st.session_state.players)

st.title("🏆 ЛИГА БЕЛКИ (РЕГЛАМЕНТ: 10 ЭТАПОВ)")

if st.button("🔄 Синхронизировать с Google Таблицей"):
    force_reload()

st.markdown("---")
col_sel1, col_sel2 = st.columns([2, 3])
with col_sel1:
    selected_stage = st.selectbox("🎯 Выберите этап соревнования:", list(range(1, 11)), index=0)

# --- ИНИЦИАЛИЗАЦИЯ И СБОР СТАТИСТИКИ ---
global_stats = {p: {
    "Очки": 0, "Игры": 0, "Победы": 0, "Поражения": 0,
    "глаза_выигр": 0, "глаза_проигр": 0, "глаза_разница": 0,
    "партия_выигр": 0, "партия_проигр": 0, "партия_разница": 0,
    "голый_выигр": 0, "голый_проигр": 0, "голый_разница": 0,
    "яйца_выигр": 0, "яйца_проигр": 0, "яйца_разница": 0,
    "сокыр_выигр": 0, "сокыр_проигр": 0, "сокыр_разница": 0
} for p in st.session_state.players}

stage_stats = {p: {
    "Очки": 0, "Игры": 0, "Победы": 0, "Поражения": 0,
    "глаза_выигр": 0, "глаза_проигр": 0, "глаза_разница": 0,
    "партия_выигр": 0, "партия_проигр": 0, "партия_разница": 0,
    "голый_выигр": 0, "голый_проигр": 0, "голый_разница": 0,
    "яйца_выигр": 0, "яйца_проигр": 0, "яйца_разница": 0,
    "сокыр_выигр": 0, "сокыр_проигр": 0, "сокыр_разница": 0
} for p in st.session_state.players}

pairs_stats = {}

stage_schedule = [s for s in DYNAMIC_SCHEDULE if s["stage"] == selected_stage]
stage_matches_sets = []
for s in stage_schedule:
    if s['m1_p1'] and s['m1_p2'] and s['m1_p1'] != ("—", "—"):
        stage_matches_sets.append((frozenset(s['m1_p1']), frozenset(s['m1_p2'])))
    if s['m2_p1'] and s['m2_p2'] and s['m2_p1'] != ("—", "—"):
        stage_matches_sets.append((frozenset(s['m2_p1']), frozenset(s['m2_p2'])))

match_results = {}

for game in st.session_state.games:
    try:
        w_team = game.get("win_team", [])
        l_team = game.get("loss_team", [])
        if len(w_team) < 2 or len(l_team) < 2: continue
        if not (all(p in global_stats for p in w_team) and all(p in global_stats for p in l_team)): continue
            
        win_pts = int(game.get("win_points", 0))
        loss_pts = int(game.get("loss_points", 0))
        win_eyes = int(game.get("win_eyes", 12))
        loss_eyes = int(game.get("loss_eyes", 0))

        win_pair = tuple(sorted(w_team))
        loss_pair = tuple(sorted(l_team))

        key_match = (tuple(win_pair), tuple(loss_pair))
        match_results[key_match] = f"🟢 {win_pair[0]}+{win_pair[1]} ({win_eyes} гл.) vs 🔴 {loss_pair[0]}+{loss_pair[1]} ({loss_eyes} гл.)"

        is_this_stage_game = False
        game_pair_set = (frozenset(w_team), frozenset(l_team))
        reversed_game_pair_set = (frozenset(l_team), frozenset(w_team))
        if (game_pair_set in stage_matches_sets) or (reversed_game_pair_set in stage_matches_sets):
            is_this_stage_game = True

        for pair, pts, is_win, eyes_scored, eyes_conceded in [
            (win_pair, win_pts, True, win_eyes, loss_eyes), 
            (loss_pair, loss_pts, False, loss_eyes, win_eyes)
        ]:
            if pair not in pairs_stats:
                pairs_stats[pair] = {
                    "Очки": 0, "Игры": 0, "Победы": 0, "Забитые глаза": 0, "Пропущенные глаза": 0,
                    "[Партии] Выиграно": 0, "[Партии] Проиграно": 0, "[Голый] Выиграно": 0, "[Голый] Проиграно": 0,
                    "[Яйца] Повесили": 0, "[Яйца] Получили": 0, "[Сокыр] Выиграно": 0, "[Сокыр] Проиграно": 0
                }
            pairs_stats[pair]["Очки"] += pts
            pairs_stats[pair]["Игры"] += 1
            pairs_stats[pair]["Забитые глаза"] += eyes_scored
            pairs_stats[pair]["Пропущенные глаза"] += eyes_conceded
            if is_win: pairs_stats[pair]["Победы"] += 1

        raw_status = str(game.get("raw_status", ""))
        is_eggs = str(game.get("eggs_happened", "")).upper() in ["TRUE", "1", "ИСТИНА"]

        for p in w_team:
            global_stats[p]["Очки"] += win_pts
            global_stats[p]["Игры"] += 1
            global_stats[p]["Победы"] += 1
            global_stats[p]["глаза_выигр"] += win_eyes
            global_stats[p]["глаза_проигр"] += loss_eyes
            if is_this_stage_game:
                stage_stats[p]["Очки"] += win_pts
                stage_stats[p]["Игры"] += 1
                stage_stats[p]["Победы"] += 1
                stage_stats[p]["глаза_выигр"] += win_eyes
                stage_stats[p]["глаза_проигр"] += loss_eyes

            if "Партия" in raw_status:
                global_stats[p]["партия_выигр"] += 1
                if is_this_stage_game: stage_stats[p]["партия_выигр"] += 1
            elif "Голый" in raw_status:
                global_stats[p]["голый_выигр"] += 1
                if is_this_stage_game: stage_stats[p]["голый_выигр"] += 1
            elif "Сокыр" in raw_status:
                global_stats[p]["сокыр_выигр"] += 1
                if is_this_stage_game: stage_stats[p]["сокыр_выигр"] += 1
            if is_eggs:
                global_stats[p]["яйца_выигр"] += 1
                if is_this_stage_game: stage_stats[p]["яйца_выигр"] += 1
                
        for p in l_team:
            global_stats[p]["Очки"] += loss_pts
            global_stats[p]["Игры"] += 1
            global_stats[p]["Поражения"] += 1
            global_stats[p]["глаза_выигр"] += loss_eyes
            global_stats[p]["глаза_проигр"] += win_eyes
            if is_this_stage_game:
                stage_stats[p]["Очки"] += loss_pts
                stage_stats[p]["Игры"] += 1
                stage_stats[p]["Поражения"] += 1
                stage_stats[p]["глаза_выигр"] += loss_eyes
                stage_stats[p]["глаза_проигр"] += win_eyes

            if "Партия" in raw_status:
                global_stats[p]["партия_проигр"] += 1
                if is_this_stage_game: stage_stats[p]["партия_проигр"] += 1
            elif "Голый" in raw_status:
                global_stats[p]["голый_проигр"] += 1
                if is_this_stage_game: stage_stats[p]["голый_проигр"] += 1
            elif "Сокыр" in raw_status:
                global_stats[p]["сокыр_проигр"] += 1
                if is_this_stage_game: stage_stats[p]["сокыр_проигр"] += 1
            if is_eggs:
                global_stats[p]["яйца_проигр"] += 1
                if is_this_stage_game: stage_stats[p]["яйца_проигр"] += 1
    except:
        continue

for p in global_stats:
    global_stats[p]["глаза_разница"] = global_stats[p]["глаза_выигр"] - global_stats[p]["глаза_проигр"]
    global_stats[p]["партия_разница"] = global_stats[p]["партия_выигр"] - global_stats[p]["партия_проигр"]
    global_stats[p]["голый_разница"] = global_stats[p]["голый_выигр"] - global_stats[p]["голый_проигр"]
    global_stats[p]["яйца_разница"] = global_stats[p]["яйца_выигр"] - global_stats[p]["яйца_проигр"]
    global_stats[p]["сокыр_разница"] = global_stats[p]["сокыр_выигр"] - global_stats[p]["сокыр_проигр"]

for p in stage_stats:
    stage_stats[p]["глаза_разница"] = stage_stats[p]["глаза_выигр"] - stage_stats[p]["глаза_проигр"]
    stage_stats[p]["партия_разница"] = stage_stats[p]["партия_выигр"] - stage_stats[p]["партия_проигр"]
    stage_stats[p]["голый_разница"] = stage_stats[p]["голый_выигр"] - stage_stats[p]["голый_проигр"]
    stage_stats[p]["яйца_разница"] = stage_stats[p]["яйца_выигр"] - stage_stats[p]["яйца_проигр"]
    stage_stats[p]["сокыр_разница"] = stage_stats[p]["сокыр_выигр"] - stage_stats[p]["сокыр_проигр"]

# --- ТАБЛИЦА ЭТАПА ---
st.markdown(f"### 📊 Турнирная таблица этапа №{selected_stage}")

df_stage_raw = pd.DataFrame.from_dict(stage_stats, orient='index').reset_index()
df_stage_raw.rename(columns={"index": "Игрок", "Очки": "Очки этапа", "Игры": "Игр сыграно"}, inplace=True)
df_stage_sorted = df_stage_raw.sort_values(by=["Очки этапа", "глаза_разница"], ascending=[False, False]).reset_index(drop=True)

multi_stage_df = pd.DataFrame()
multi_stage_df[("", "Игрок")] = df_stage_sorted["Игрок"]
multi_stage_df[("", "Очки этапа")] = df_stage_sorted["Очки этапа"]
multi_stage_df[("", "Игр сыграно")] = df_stage_sorted["Игр сыграно"]

for tag in ["партия", "глаза", "голый", "яйца", "сокыр"]:
    multi_stage_df[(tag, "выигр")] = df_stage_sorted[f"{tag}_выигр"]
    multi_stage_df[(tag, "проигр")] = df_stage_sorted[f"{tag}_проигр"]
    multi_stage_df[(tag, "разница")] = df_stage_sorted[f"{tag}_разница"]

multi_stage_df.columns = pd.MultiIndex.from_tuples(multi_stage_df.columns)
multi_stage_df.index = multi_stage_df.index + 1

st.dataframe(multi_stage_df, use_container_width=True)
st.markdown("---")

# --- АНАЛИТИКА ---
st.markdown("### 📈 Раздел аналитики турнира")
tab_schedule, tab_leaderboard, tab_partii, tab_glaza, tab_golye, tab_yaica, tab_sokyry, tab_pairs = st.tabs([
    "📅 Игры (Календарь этапа)", "🏆 Главная турнирная таблица", "🃏 Партии", "👁️ Глаза", "🔥 Голые", "🥚 Яйца", "🕶️ Сокыры", "👥 Рейтинг связок"
])

with tab_schedule:
    st.markdown(f"#### 📅 Расписание матчей этапа №{selected_stage} (Всего 63 игры за этап)")
    stage_data = []
    for s in stage_schedule:
        m1_text = f"{s['m1_p1'][0]} + {s['m1_p1'][1]} 🆚 {s['m1_p2'][0]} + {s['m1_p2'][1]}" if s['m1_p1'] != ("—", "—") else "—"
        key1 = (tuple(sorted(s['m1_p1'])), tuple(sorted(s['m1_p2'])))
        res1 = match_results.get(key1, match_results.get((key1[1], key1[0]), "Предстоит сыграть")) if s['m1_p1'] != ("—", "—") else "—"

        m2_text = f"{s['m2_p1'][0]} + {s['m2_p1'][1]} 🆚 {s['m2_p2'][0]} + {s['m2_p2'][1]}" if s['m2_p1'] != ("—", "—") else "—"
        key2 = (tuple(sorted(s['m2_p1'])), tuple(sorted(s['m2_p2'])))
        res2 = match_results.get(key2, match_results.get((key2[1], key2[0]), "Предстоит сыграть")) if s['m2_p1'] != ("—", "—") else "—"

        stage_data.append({
            "Игровой круг / Тур": f"Тур {s['tour']}", 
            "Матч 1": m1_text, "Результат Матча 1": res1, 
            "Матч 2": m2_text, "Результат Матча 2": res2,
            "Исключенные из тура": s['bypass']
        })
    st.dataframe(pd.DataFrame(stage_data), use_container_width=True, hide_index=True)

with tab_leaderboard:
    st.markdown("#### 🏆 Главная турнирная таблица (Все этапы)")
    df_leaderboard = pd.DataFrame.from_dict(global_stats, orient='index').reset_index()
    df_leaderboard.rename(columns={"index": "Игрок", "Очки": "Всего очков", "Игры": "Сыграно игр"}, inplace=True)
    df_sorted = df_leaderboard.sort_values(by=["Всего очков", "глаза_разница"], ascending=[False, False]).reset_index(drop=True)

    multi_df = pd.DataFrame()
    multi_df[("", "Игрок")] = df_sorted["Игрок"]
    multi_df[("", "Всего очков")] = df_sorted["Всего очков"]
    multi_df[("", "Сыграно игр")] = df_sorted["Сыграно игр"]

    for tag in ["партия", "глаза", "голый", "яйца", "сокыр"]:
        multi_df[(tag, "выигр")] = df_sorted[f"{tag}_выигр"]
        multi_df[(tag, "проигр")] = df_sorted[f"{tag}_проигр"]
        multi_df[(tag, "разница")] = df_sorted[f"{tag}_разница"]

    multi_df.columns = pd.MultiIndex.from_tuples(multi_df.columns)
    multi_df.index = multi_df.index + 1
    st.dataframe(multi_df, use_container_width=True)

with tab_partii:
    st.markdown("#### Аналитика по Партиям")
    df_partii = df_leaderboard[["Игрок", "партия_выигр", "партия_проигр", "партия_разница"]].copy()
    df_partii.columns = ["Игрок", "Побед", "Проигрыш", "Разница"]
    st.dataframe(df_partii.sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_glaza:
    st.markdown("#### Аналитика по набранным и упущенным глазам")
    df_glaza = df_leaderboard[["Игrok", "глаза_выигр", "глаза_проигр", "глаза_разница"]].copy() if "Игrok" in df_leaderboard else df_leaderboard[["Игрок", "глаза_выигр", "глаза_проигр", "глаза_разница"]].copy()
    df_glaza.columns = ["Игрок", "Побед (Набрано)", "Проигрыш (Упущено)", "Разница"]
    st.dataframe(df_glaza.sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_golye:
    st.markdown("#### Аналитика по Голым партиям")
    df_golye = df_leaderboard[["Игрок", "голый_выигр", "голый_проигр", "голый_разница"]].copy()
    df_golye.columns = ["Игрок", "Побед", "Проигрыш", "Разница"]
    st.dataframe(df_golye.sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_yaica:
    st.markdown("#### Аналитика по Яйцам")
    df_yaica = df_leaderboard[["Игрок", "яйца_выигр", "яйца_проигр", "яйца_разница"]].copy()
    df_yaica.columns = ["Игрок", "Побед (Повесили)", "Проигрыш (Получили)", "Разница"]
    st.dataframe(df_yaica.sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_sokyry:
    st.markdown("#### Аналитика по Сокырам")
    df_sokyry = df_leaderboard[["Игрок", "сокыр_выигр", "сокыр_проигр", "сокыр_разница"]].copy()
    df_sokyry.columns = ["Игрок", "Побед", "Проигрыш", "Разница"]
    st.dataframe(df_sokyry.sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_pairs:
    if pairs_stats:
        p_list = []
        for k, v in pairs_stats.items():
            p_list.append({
                "Пара игроков": f"{k[0]} 🤝 {k[1]}", "Очки": v["Очки"], "Игры": v["Игры"], "Победы": v["Победы"],
                "Забитые глаза": v["Забитые глаза"], "Пропущенные глаза": v["Пропущенные глаза"], "Разница глаз": v["Забитые глаза"] - v["Пропущенные глаза"]
            })
        st.dataframe(pd.DataFrame(p_list).sort_values(by="Очки", ascending=False).reset_index(drop=True), use_container_width=True)
    else:
        st.info("Статистики парных матчей пока нет.")

st.markdown("---")

# --- РЕГИСТРАЦИЯ И УПРАВЛЕНИЕ МАТЧАМИ ---
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
        status = st.selectbox("What was dealt?", ["Партия (3 очка)", "Голый (3 очка)", "Сокыр (12 очков)"])
        eggs = st.checkbox("Повесили «Яйца» (+1 очко победителю)")

        if status == "Голый (3 очка)":
            win_eyes_val, loss_eyes_val, disabled_eyes = 12, 0, True
        else:
            win_eyes_val, loss_eyes_val, disabled_eyes = 12, 4, False
            
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            final_win_eyes = 16 if eggs else win_eyes_val
            st.info(f"Глаза Победителей: {final_win_eyes}")
        with col_e2:
            if disabled_eyes:
                loss_eyes_input = 0
                st.info("Глаза Проигравших: 0")
            else:
                loss_eyes_input = st.number_input("Глаза Проигравших (0-11)", min_value=0, max_value=11, value=loss_eyes_val, step=1)
        
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
                        f"{p1}, {p2}", f"{p3}, {p4}", int(win_pts), int(loss_pts),
                        str(status), str(eggs).upper(), f"{status} {'+ Яйца' if eggs else ''}",
                        float(time.time()), int(final_win_eyes), int(loss_eyes_input)
                    ])
                    st.success("Результат успешно занесен в облако!")
                    time.sleep(1.0)
                    force_reload()
                except Exception as e:
                    st.error(f"Ошибка сохранения: {e}")

    st.markdown("### 🛠️ Корректировка результатов")
    with st.expander("❌ Удалить конкретную игру по номеру", expanded=False):
        if st.session_state.games:
            game_numbers = list(range(1, len(st.session_state.games) + 1))
            selected_game_num = st.selectbox("Выберите номер матча для удаления:", game_numbers)
            g_idx = selected_game_num - 1
            game_info = st.session_state.games[g_idx]
            st.info(f"**Матч №{selected_game_num}:** Победители: {', '.join(game_info['win_team'])} | Проигравшие: {', '.join(game_info['loss_team'])}")
            
            if st.button("УДАЛИТЬ ВЫБРАННЫЙ МАТЧ"):
                if match_password != "6666":
                    st.error("🔒 Введите пароль администратора!")
                else:
                    try:
                        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                        worksheet_g = sh.worksheet("games")
                        worksheet_g.delete_rows(selected_game_num + 1)
                        st.success("Матч успешно удален!")
                        time.sleep(1.0)
                        force_reload()
                    except Exception as e:
                        st.error(f"Ошибка удаления: {e}")
        else:
            st.info("База матчей пуста.")

with col_bottom2:
    st.markdown("### 👥 Участники Лиги")
    st.write(pd.DataFrame(st.session_state.players, columns=["Имя участника"]).to_html(index=False), unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("#### ⚙️ Панель управления составом")
    manage_password = st.text_input("🔑 Пароль управления игроками:", type="password")
    
    new_player_name = st.text_input("Имя нового участника:")
    if st.button("Добавить участника"):
        if manage_password != "6666": st.error("Неверный пароль!")
        elif not new_player_name.strip(): st.warning("Введите имя.")
        elif new_player_name.strip() in st.session_state.players: st.warning("Уже есть.")
        else:
            try:
                sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                worksheet_p = sh.worksheet("players")
                worksheet_p.append_row([new_player_name.strip()])
                st.success("Игрок добавлен!")
                time.sleep(1.0)
                force_reload()
            except Exception as e: st.error(f"Ошибка: {e}")
                
    player_to_remove = st.selectbox("Выберите игрока для исключения:", st.session_state.players)
    if st.button("Исключить выбранного игрока"):
        if manage_password != "6666": st.error("Неверный пароль!")
        else:
            try:
                sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                worksheet_p = sh.worksheet("players")
                cells = worksheet_p.findall(player_to_remove)
                if cells:
                    worksheet_p.delete_rows(cells[0].row)
                    st.success("Игрок исключен.")
                    time.sleep(1.0)
                    force_reload()
                else: st.error("Не найден в таблице.")
            except Exception as e: st.error(f"Ошибка: {e}")

    st.markdown("---")
    st.markdown("#### Сброс результатов")
    reset_password = st.text_input("🔑 Введите ключ доступа для сброса:", type="password")
    
    if st.button("🚨 СБРОСИТЬ ВСЮ ТАБЛИЦУ ДО НУЛЯ"):
        if reset_password != "5559":
            st.error("🔒 Доступ заблокирован! Неверный ключ доступа.")
        elif gc is None:
            st.error("Нет подключения к базе данных.")
        else:
            try:
                with st.spinner("Производится полная очистка базы данных матчей..."):
                    sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                    worksheet_g = sh.worksheet("games")
                    row_count = len(worksheet_g.col_values(1))
                    if row_count > 1:
                        worksheet_g.resize(rows=1)
                        worksheet_g.resize(rows=100)
                        st.success("Все данные в Google Таблице успешно стерты!")
                        time.sleep(1.5)
                        force_reload()
                    else:
                        st.info("Таблица и так абсолютно пустая!")
            except Exception as e:
                st.error(f"Сбой при очистке: {e}")
