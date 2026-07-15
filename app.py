import streamlit as st
import pandas as pd
import gspread
import time
import itertools
import requests

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
    div.stForm stButton > button:hover, div.stForm stButton > button:contains("СОХРАНИТЬ"):hover { 
        background-color: #e6b800 !important; 
        color: #000000 !important;
    }
    
    /* Зеленые кнопки действий */
    div.stButton > button {
        background-color: #1e7e34 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    /* Красные кнопки удаления/исключения */
    button:contains("УДАЛИТЬ"), button:contains("Исключить") {
        background-color: #b21f2d !important;
        color: #ffffff !important;
        border: 2px solid #dc3545 !important;
    }
    
    /* СТИЛИЗАЦИЯ ВКЛАДОК */
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

# Инициализация подключения через gspread (ресурс кэшируем)
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
DEFAULT_PLAYERS = ["Азирхан", "Аманат", "Данияр", "Елдар", "Мерхат", "Рустем", "Талгат", "Шынгыс"]

# НАДЁЖНАЯ ФУНКЦИЯ ЧТЕНИЯ (Без @st.cache_data, чтобы исключить зависание старых данных)
def load_fresh_data():
    if gc is None:
        return DEFAULT_PLAYERS.copy(), []
    try:
        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
        
        # Загрузка списка игроков
        try:
            worksheet_p = sh.worksheet("players")
            players = [x for x in worksheet_p.col_values(1) if x and x != 'Имя']
            if not players:
                players = DEFAULT_PLAYERS.copy()
        except:
            players = DEFAULT_PLAYERS.copy()
            
        # Загрузка истории матчей
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

# Инициализация сессии данных при первом запуске
if "data_loaded" not in st.session_state or st.sidebar.button("🔄 Сбросить кэш приложения"):
    p_fresh, g_fresh = load_fresh_data()
    st.session_state.players = p_fresh
    st.session_state.games = g_fresh
    st.session_state.data_loaded = True

# Удобная функция для принудительного обновления стейта
def force_reload():
    p_fresh, g_fresh = load_fresh_data()
    st.session_state.players = p_fresh
    st.session_state.games = g_fresh
    st.rerun()

# --- СИСТЕМА НАЧИСЛЕНИЯ ОЧКОВ ---
POINTS_DICT = {
    "Партия (2 очка)": 2,
    "Голый (3 очка)": 3,
    "Сокыр (12 очков)": 12
}

def calculate_match_points(status, eggs):
    base_points = POINTS_DICT[status]
    return (base_points + 1, 0) if eggs else (base_points, 0)

# --- АЛГОРИТМ ГЕНЕРАЦИИ УНИКАЛЬНОГО РАСПИСАНИЯ ---
def generate_balanced_schedule(player_list):
    if len(player_list) < 4:
        return []
    all_pairs = list(itertools.combinations(player_list, 2))
    used_pairs = set()
    schedule = []
    tour_num = 1
    max_attempts = 100
    for _ in range(max_attempts):
        if len(used_pairs) >= len(all_pairs): break
        available_pairs = [p for p in all_pairs if p not in used_pairs]
        if len(available_pairs) < 2: break
        tour_matches = []
        active_players_in_tour = set()
        match1_found = False
        for p1 in available_pairs:
            for p2 in available_pairs:
                if set(p1).isdisjoint(set(p2)):
                    tour_matches.append((p1, p2))
                    active_players_in_tour.update(p1)
                    active_players_in_tour.update(p2)
                    used_pairs.add(p1)
                    used_pairs.add(p2)
                    match1_found = True
                    break
            if match1_found: break
        if not match1_found: break
        remaining_pairs = [p for p in available_pairs if p not in used_pairs and set(p).isdisjoint(active_players_in_tour)]
        match2_found = False
        for p3 in remaining_pairs:
            for p4 in remaining_pairs:
                if set(p3).isdisjoint(set(p4)):
                    tour_matches.append((p3, p4))
                    used_pairs.add(p3)
                    used_pairs.add(p4)
                    match2_found = True
                    break
            if match2_found: break
        if len(tour_matches) >= 1:
            m1 = tour_matches[0]
            m2 = tour_matches[1] if len(tour_matches) > 1 else (None, None)
            schedule.append({
                "tour": tour_num, "m1_p1": m1[0], "m1_p2": m1[1],
                "m2_p1": m2[0] if m2 else None, "m2_p2": m2[1] if m2 else None
            })
            tour_num += 1
    return schedule

DYNAMIC_SCHEDULE = generate_balanced_schedule(st.session_state.players)

# --- РАСЧЕТ СТАТИСТИКИ И ГТТ ---
stats = {p: {
    "Очки": 0, "Игры": 0, "Победы": 0, "Поражения": 0,
    "Забитые глаза": 0, "Пропущенные глаза": 0, "Разница глаз": 0,
    "[Партии] Выиграно": 0, "[Партии] Проиграно": 0, "[Партии] Разница": 0,
    "[Голый] Выиграно": 0, "[Голый] Проиграно": 0, "[Голый] Разница": 0,
    "[Яйца] Повесили": 0, "[Яйца] Получили": 0, "[Яйца] Разница": 0,
    "[Сокыр] Выиграно": 0, "[Сокыр] Проиграно": 0, "[Сокыр] Разница": 0
} for p in st.session_state.players}

pairs_stats = {}

for game in st.session_state.games:
    try:
        w_team = game.get("win_team", [])
        l_team = game.get("loss_team", [])
        if len(w_team) < 2 or len(l_team) < 2: continue
        if not (all(p in stats for p in w_team) and all(p in stats for p in l_team)): continue
            
        win_pts = int(game.get("win_points", 0))
        loss_pts = int(game.get("loss_points", 0))
        win_eyes = int(game.get("win_eyes", 12))
        loss_eyes = int(game.get("loss_eyes", 0))

        win_pair = tuple(sorted(w_team))
        loss_pair = tuple(sorted(l_team))

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
            stats[p]["Очки"] += win_pts
            stats[p]["Игры"] += 1
            stats[p]["Победы"] += 1
            stats[p]["Забитые глаза"] += win_eyes
            stats[p]["Пропущенные глаза"] += loss_eyes
            if "Партия" in raw_status:
                stats[p]["[Партии] Выиграно"] += 1
                pairs_stats[win_pair]["[Партии] Выиграно"] += 1
            elif "Голый" in raw_status:
                stats[p]["[Голый] Выиграно"] += 1
                pairs_stats[win_pair]["[Голый] Выиграно"] += 1
            elif "Сокыр" in raw_status:
                stats[p]["[Сокыр] Выиграно"] += 1
                pairs_stats[win_pair]["[Сокыр] Выиграно"] += 1
            if is_eggs:
                stats[p]["[Яйца] Повесили"] += 1
                pairs_stats[win_pair]["[Яйца] Повесили"] += 1
                
        for p in l_team:
            stats[p]["Очки"] += loss_pts
            stats[p]["Игры"] += 1
            stats[p]["Поражения"] += 1
            stats[p]["Забитые глаза"] += loss_eyes
            stats[p]["Пропущенные глаза"] += win_eyes
            if "Партия" in raw_status:
                stats[p]["[Партии] Проиграно"] += 1
                pairs_stats[loss_pair]["[Партии] Проиграно"] += 1
            elif "Голый" in raw_status:
                stats[p]["[Голый] Проиграно"] += 1
                pairs_stats[loss_pair]["[Голый] Проиграно"] += 1
            elif "Сокыр" in raw_status:
                stats[p]["[Сокыр] Проиграно"] += 1
                pairs_stats[loss_pair]["[Сокыр] Проиграно"] += 1
            if is_eggs:
                stats[p]["[Яйца] Получили"] += 1
                pairs_stats[loss_pair]["[Яйца] Получили"] += 1
    except:
        continue

for p in stats:
    stats[p]["Разница глаз"] = stats[p]["Забитые глаза"] - stats[p]["Пропущенные глаза"]
    stats[p]["[Партии] Разница"] = stats[p]["[Партии] Выиграно"] - stats[p]["[Партии] Проиграно"]
    stats[p]["[Голый] Разница"] = stats[p]["[Голый] Выиграно"] - stats[p]["[Голый] Проиграно"]
    stats[p]["[Яйца] Разница"] = stats[p]["[Яйца] Повесили"] - stats[p]["[Яйца] Получили"]
    stats[p]["[Сокыр] Разница"] = stats[p]["[Сокыр] Выиграно"] - stats[p]["[Сокыр] Проиграно"]

df_leaderboard = pd.DataFrame.from_dict(stats, orient='index').reset_index()
df_leaderboard.rename(columns={"index": "Игрок", "Очки": "Всего очков", "Игры": "Сыграно игр"}, inplace=True)

st.title("🏆 КЛАССИЧЕСКАЯ ЛИГА БЕЛКИ")

if st.button("🔄 Синхронизировать с Google Таблицей"):
    force_reload()

st.markdown("### 📊 Главная турнирная таблица (ГТТ)")

gtt_cols = [
    "Игрок", "Всего очков", "Сыграно игр",
    "[Партии] Выиграно", "[Партии] Проиграно", "[Партии] Разница",
    "Забитые глаза", "Пропущенные глаза", "Разница глаз",
    "[Голый] Выиграно", "[Голый] Проиграно", "[Голый] Разница",
    "[Яйца] Повесили", "[Яйца] Получили", "[Яйца] Разница",
    "[Сокыр] Выиграно", "[Сокыр] Проиграно", "[Сокыр] Разница"
]

df_main = df_leaderboard.sort_values(by=["Всего очков", "Разница глаз"], ascending=[False, False])[gtt_cols].reset_index(drop=True)
df_main.index = df_main.index + 1
st.dataframe(df_main, use_container_width=True)

st.markdown("---")

tab_calendar, tab_positive, tab_negative, tab_pairs = st.tabs([
    "📅 Календарь и История", "🚀 Раздали (Выигрыши)", "📉 Словленные (Проигрыши)", "👥 Рейтинг связок"
])

# 1. ОБЪЕДИНЕННЫЙ КАЛЕНДАРЬ И ИСТОРИЯ
with tab_calendar:
    st.markdown("#### Расписание туров и Результаты сыгранных встреч")
    match_results = {}
    for g in st.session_state.games:
        try:
            wt = sorted(g['win_team'])
            lt = sorted(g['loss_team'])
            key = (tuple(wt), tuple(lt))
            match_results[key] = f"🟢 {wt[0]}+{wt[1]} ({g['win_eyes']} глазов) vs 🔴 {lt[0]}+{lt[1]} ({g['loss_eyes']} глазов) [{g['status']}]"
        except:
            continue

    sched_data = []
    for s in DYNAMIC_SCHEDULE:
        if s['m1_p1'] and s['m1_p2']:
            pair1_1 = sorted(s['m1_p1'])
            pair1_2 = sorted(s['m1_p2'])
            key1 = (tuple(pair1_1), tuple(pair1_2))
            res1 = match_results.get(key1, match_results.get((tuple(pair1_2), tuple(pair1_1)), "Предстоит сыграть"))
            m1_text = f"{pair1_1[0]} + {pair1_1[1]} 🆚 {pair1_2[0]} + {pair1_2[1]}"
        else:
            m1_text, res1 = "—", "—"

        if s['m2_p1'] and s['m2_p2']:
            pair2_1 = sorted(s['m2_p1'])
            pair2_2 = sorted(s['m2_p2'])
            key2 = (tuple(pair2_1), tuple(pair2_2))
            res2 = match_results.get(key2, match_results.get((tuple(pair2_2), tuple(pair2_1)), "Предстоит сыграть"))
            m2_text = f"{pair2_1[0]} + {pair2_1[1]} 🆚 {pair2_2[0]} + {pair2_2[1]}"
        else:
            m2_text, res2 = "—", "—"

        sched_data.append({
            "Тур": f"Тур {s['tour']}", "Матч 1": m1_text, "Результат Матча 1": res1, "Матч 2": m2_text, "Результат Матча 2": res2
        })
    st.dataframe(pd.DataFrame(sched_data), use_container_width=True, hide_index=True)

# 2, 3, 4 Вкладки статистики
with tab_positive:
    sub_pos_tabs = st.tabs(["Партии", "Голый", "Яйца", "Сокыр", "Забитые Глаза"])
    with sub_pos_tabs[0]: st.dataframe(df_leaderboard[["Игрок", "[Партии] Выиграно", "[Партии] Разница"]].sort_values(by="[Партии] Выиграно", ascending=False), use_container_width=True, hide_index=True)
   # Стало (исправлено):
with sub_pos_tabs[1]: st.dataframe(df_leaderboard[["Игрок", "[Голый] Выиграно", "[Голый] Разница"]].sort_values(by="[Голый] Выиграно", ascending=False), use_container_width=True, hide_index=True)
    with sub_pos_tabs[2]: st.dataframe(df_leaderboard[["Игрок", "[Яйца] Повесили", "[Яйца] Разница"]].sort_values(by="[Яйца] Повесили", ascending=False), use_container_width=True, hide_index=True)
    with sub_pos_tabs[3]: st.dataframe(df_leaderboard[["Игрок", "[Сокыр] Выиграно", "[Сокыр] Разница"]].sort_values(by="[Сокыр] Выиграно", ascending=False), use_container_width=True, hide_index=True)
    with sub_pos_tabs[4]: st.dataframe(df_leaderboard[["Игрок", "Забитые глаза", "Разница глаз"]].sort_values(by="Забитые глаза", ascending=False), use_container_width=True, hide_index=True)

with tab_negative:
    sub_neg_tabs = st.tabs(["Проиграно Партий", "Проиграно Голых", "Получили Яйца", "Проиграно Сокыров", "Пропущенные Глаза"])
    with sub_neg_tabs[0]: st.dataframe(df_leaderboard[["Игрок", "[Партии] Проиграно", "[Партии] Разница"]].sort_values(by="[Партии] Проиграно", ascending=False), use_container_width=True, hide_index=True)
    with sub_neg_tabs[1]: st.dataframe(df_leaderboard[["Игрок", "[Голый] Проиграно", "[Голый] Разница"]].sort_values(by="[Голый] Проиграно", ascending=False), use_container_width=True, hide_index=True)
    with sub_neg_tabs[2]: st.dataframe(df_leaderboard[["Игрок", "[Яйца] Получили", "[Яйца] Разница"]].sort_values(by="[Яйца] Получили", ascending=False), use_container_width=True, hide_index=True)
    with sub_neg_tabs[3]: st.dataframe(df_leaderboard[["Игрок", "[Сокыр] Проиграно", "[Сокыр] Разница"]].sort_values(by="[Сокыр] Проиграно", ascending=False), use_container_width=True, hide_index=True)
    with sub_neg_tabs[4]: st.dataframe(df_leaderboard[["Игрок", "Пропущенные глаза", "Разница глаз"]].sort_values(by="Пропущенные глаза", ascending=False), use_container_width=True, hide_index=True)

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
        st.info("Статистики сыгранных парных матчей пока нет.")

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
        status = st.selectbox("Что дали?", ["Партия (2 очка)", "Голый (3 очка)", "Сокыр (12 очков)"])
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
                    force_reload()  # МГНОВЕННЫЙ СБРОС И ПЕРЕЗАГРУЗКА ДАННЫХ
                except Exception as e:
                    st.error(f"Ошибка сохранения: {e}")

    # Корректировка результатов
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

# --- УПРАВЛЕНИЕ УЧАСТНИКАМИ ---
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
