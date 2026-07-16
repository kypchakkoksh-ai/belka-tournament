import streamlit as st
import pandas as pd
import gspread
import time

# Настройка страницы
st.set_page_config(page_title="Лига Белки — 45 Команд", layout="wide", page_icon="🏆")

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

# --- СПИСОК 45 КОМАНД ---
TEAMS = {
    1: "Данияр + Азирхан", 2: "Данияр + Талгат", 3: "Данияр + Елдар", 4: "Данияр + Марат",
    5: "Данияр + Рустем", 6: "Данияр + Аманат", 7: "Данияр + Мерхат", 8: "Данияр + Шынгыс",
    9: "Данияр + Ерлан", 10: "Азирхан + Талгат", 11: "Азирхан + Елдар", 12: "Азирхан + Марат",
    13: "Азирхан + Рустем", 14: "Азирхан + Аманат", 15: "Азирхан + Мерхат", 16: "Азирхан + Шынгыс",
    17: "Азирхан + Ерлан", 18: "Талгат + Елдар", 19: "Талгат + Марат", 20: "Талгат + Рустем",
    21: "Талгат + Аманат", 22: "Талгат + Мерхат", 23: "Талгат + Шынгыс", 24: "Талгат + Ерлан",
    25: "Елдар + Марат", 26: "Елдар + Рустем", 27: "Елдар + Аманат", 28: "Елдар + Мерхат",
    29: "Елдар + Шынгыс", 30: "Елдар + Ерлан", 31: "Марат + Рустем", 32: "Марат + Аманат",
    33: "Марат + Мерхат", 34: "Марат + Шынгыс", 35: "Марат + Ерлан", 36: "Рустем + Аманат",
    37: "Рустем + Мерхат", 38: "Рустем + Шынгыс", 39: "Рустем + Ерлан", 40: "Аманат + Мерхат",
    41: "Аманат + Шынгыс", 42: "Аманат + Ерлан", 43: "Мерхат + Шынгыс", 44: "Мерхат + Ерлан",
    45: "Шынгыс + Ерлан"
}

# --- ГЕНЕРАЦИЯ ЦИКЛИЧЕСКОГО РАСПИСАНИЯ (45 ТУРОВ) ---
@st.cache_data
def generate_berger_45_tours():
    n_teams = 45
    pool = list(range(1, n_teams + 1))
    full_schedule = {}
    
    for tour in range(1, n_teams + 1):
        bye_team = pool[-tour]
        tour_pool = pool[n_teams - tour:] + pool[:n_teams - tour]
        tour_pool.remove(bye_team)
        
        matches = []
        for i in range(22):
            t1 = tour_pool[i]
            t2 = tour_pool[-(i + 1)]
            matches.append((t1, t2))
            
        full_schedule[tour] = {
            "bye": bye_team,
            "matches": matches
        }
    return full_schedule

COMPLET_SCHEDULE = generate_berger_45_tours()

def load_fresh_data():
    if gc is None:
        return []
    try:
        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
        try:
            worksheet_g = sh.worksheet("games")
            all_records = worksheet_g.get_all_records()
            return pd.DataFrame(all_records).to_dict(orient='records') if all_records else []
        except:
            return []
    except Exception as e:
        st.error(f"Ошибка сети при получении данных: {e}")
        return []

if "data_loaded" not in st.session_state or st.sidebar.button("🔄 Сбросить кэш приложения"):
    st.session_state.games = load_fresh_data()
    st.session_state.data_loaded = True

def force_reload():
    st.session_state.games = load_fresh_data()
    st.rerun()

POINTS_DICT = {
    "Партия (3 очка)": 3,
    "Голый (3 очка)": 3,
    "Сокыр (12 очков)": 12
}

st.title("🏆 ЛИГА БЕЛКИ (РЕГЛАМЕНТ: 45 ТУРОВ / 45 КОМАНД)")

if st.button("🔄 Синхронизировать с Google Таблицей"):
    force_reload()

st.markdown("---")
col_sel1, _ = st.columns([2, 3])
with col_sel1:
    selected_tour = st.selectbox("🎯 Выберите игровой тур:", list(range(1, 46)), index=0)

# --- ИНИЦИАЛИЗАЦИЯ И СБОР СТАТИСТИКИ КОМАНД ---
team_stats = {t_id: {
    "Название": TEAMS[t_id], "Очки": 0, "Игры": 0, "Победы": 0, "Поражения": 0,
    "глаза_выигр": 0, "глаза_проигр": 0, "глаза_разница": 0,
    "партия_выигр": 0, "партия_проигр": 0, "голый_выигр": 0, "голый_проигр": 0,
    "яйца_выигр": 0, "яйца_проигр": 0, "сокыр_выигр": 0, "сокыр_проигр": 0
} for t_id in TEAMS}

match_results = {}

for game in st.session_state.games:
    try:
        t1_id = int(game.get("team1_id"))
        t2_id = int(game.get("team2_id"))
        if t1_id not in team_stats or t2_id not in team_stats:
            continue
            
        win_id = int(game.get("win_team_id"))
        loss_id = t2_id if win_id == t1_id else t1_id
        
        win_pts = int(game.get("win_points", 0))
        loss_pts = int(game.get("loss_points", 0))
        win_eyes = int(game.get("win_eyes", 12))
        loss_eyes = int(game.get("loss_eyes", 0))
        
        raw_status = str(game.get("raw_status", ""))
        is_eggs = str(game.get("eggs_happened", "")).upper() in ["TRUE", "1", "ИСТИНА"]
        tour_num = int(game.get("tour_number", 0))

        # Сохраняем текстовый результат для календаря
        match_results[(tour_num, tuple(sorted([t1_id, t2_id])))] = (
            f"🟢 Команда {win_id:02d} ({win_eyes} гл.) 🆚 🔴 Команда {loss_id:02d} ({loss_eyes} гл.)"
        )

        # Начисление базовой статистики
        team_stats[win_id]["Очки"] += win_pts
        team_stats[win_id]["Игры"] += 1
        team_stats[win_id]["Победы"] += 1
        team_stats[win_id]["глаза_выигр"] += win_eyes
        team_stats[win_id]["глаза_проигр"] += loss_eyes

        team_stats[loss_id]["Очки"] += loss_pts
        team_stats[loss_id]["Игры"] += 1
        team_stats[loss_id]["Поражения"] += 1
        team_stats[loss_id]["глаза_выигр"] += loss_eyes
        team_stats[loss_id]["глаза_проигр"] += win_eyes

        # Детализация типов побед
        if "Партия" in raw_status:
            team_stats[win_id]["партия_выигр"] += 1
            team_stats[loss_id]["партия_проигр"] += 1
        elif "Голый" in raw_status:
            team_stats[win_id]["голый_выигр"] += 1
            team_stats[loss_id]["голый_проигр"] += 1
        elif "Сокыр" in raw_status:
            team_stats[win_id]["сокыр_выигр"] += 1
            team_stats[loss_id]["сокыр_проигр"] += 1
            
        if is_eggs:
            team_stats[win_id]["яйца_выигр"] += 1
            team_stats[loss_id]["яйца_проигр"] += 1
    except:
        continue

for t_id in team_stats:
    team_stats[t_id]["глаза_разница"] = team_stats[t_id]["глаза_выигр"] - team_stats[t_id]["глаза_проигр"]

# --- АНАЛИТИКА ТУРНИРА ---
st.markdown("### 📈 Раздел турнирной аналитики")
tab_leaderboard, tab_schedule, tab_details = st.tabs([
    "🏆 Главная таблица команд", "📅 Календарь встреч (Все туры)", "📊 Развернутая статистика по типам"
])

with tab_leaderboard:
    st.markdown("#### 🏆 Рейтинг всех 45 команд лиги")
    df_lb = pd.DataFrame.from_dict(team_stats, orient='index')
    df_lb.index.name = "ID"
    df_lb = df_lb.reset_index()
    df_sorted = df_lb.sort_values(by=["Очки", "глаза_разница", "Победы"], ascending=[False, False, False]).reset_index(drop=True)
    df_sorted.index = df_sorted.index + 1
    
    st.dataframe(df_sorted[["ID", "Название", "Очки", "Игры", "Победы", "Поражения", "глаза_выигр", "глаза_проигр", "глаза_разница"]], use_container_width=True)

with tab_schedule:
    t_info = COMPLET_SCHEDULE[selected_tour]
    st.markdown(f"#### 📅 Расписание встреч {selected_tour}-го тура")
    st.info(f"ℹ️ **Команда {t_info['bye']:02d} ({TEAMS[t_info['bye']]})** — Свободна от игр в этом туре (Выходной)")
    
    sched_data = []
    for m_idx, (m1, m2) in enumerate(t_info["matches"], 1):
        res = match_results.get((selected_tour, tuple(sorted([m1, m2]))), "Предстоит сыграть")
        sched_data.append({
            "Матч": f"Матч {m_idx:02d}",
            "Команда А": f"[{m1:02d}] {TEAMS[m1]}",
            "Команда Б": f"[{m2:02d}] {TEAMS[m2]}",
            "Текущий статус / Результат": res
        })
    st.dataframe(pd.DataFrame(sched_data), use_container_width=True, hide_index=True)

with tab_details:
    st.markdown("#### 🃏 Аналитика побед по категориям игр")
    df_det = pd.DataFrame.from_dict(team_stats, orient='index').reset_index()
    df_det.rename(columns={"index": "ID"}, inplace=True)
    st.dataframe(df_det[["ID", "Название", "партия_выигр", "голый_выигр", "яйца_выигр", "сокыр_выигр", "яйца_проигр"]].sort_values(by="партия_выигр", ascending=False), use_container_width=True, hide_index=True)

st.markdown("---")

# --- РЕГИСТРАЦИЯ И УПРАВЛЕНИЕ МАТЧАМИ ---
col_bottom1, col_bottom2 = st.columns([1, 1])

with col_bottom1:
    st.markdown("### ➕ Внесение результатов игры")
    match_password = st.text_input("🔑 Пароль администратора:", type="password", key="m_pass")

    with st.form("match_form_45", clear_on_submit=True):
        tour_to_save = st.number_input("Номер текущего тура для записи:", min_value=1, max_value=45, value=selected_tour)
        
        # Получаем список пар текущего выбранного тура для подсказки администратору
        current_tour_matches = COMPLET_SCHEDULE[tour_to_save]["matches"]
        match_options = [f"Матч {i:02d}: [{p[0]:02d}] vs [{p[1]:02d}]" for i, p in enumerate(current_tour_matches, 1)]
        
        selected_match_str = st.selectbox("Выберите играемую пару тура:", match_options)
        match_index = int(selected_match_str.split(":")[0].split()[1]) - 1
        t1_actual, t2_actual = current_tour_matches[match_index]
        
        st.markdown(f"**Тестируется матч:** ({t1_actual:02d}) {TEAMS[t1_actual]} **vs** ({t2_actual:02d}) {TEAMS[t2_actual]}")
        
        winner_selection = st.radio("Кто одержал победу?", [f"Команда {t1_actual:02d}", f"Команда {t2_actual:02d}"])
        win_id_input = t1_actual if winner_selection == f"Команда {t1_actual:02d}" else t2_actual
        
        st.markdown("---")
        status = st.selectbox("Тип завершения партии:", ["Партия (3 очка)", "Голый (3 очка)", "Сокыр (12 очков)"])
        eggs = st.checkbox("Повесили «Яйца» (+1 очко к победе)")

        if status == "Голый (3 очка)":
            win_eyes_val, loss_eyes_val, disabled_eyes = 12, 0, True
        else:
            win_eyes_val, loss_eyes_val, disabled_eyes = 12, 4, False
            
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            final_win_eyes = 16 if eggs else win_eyes_val
            st.info(f"Глаза победителей: {final_win_eyes}")
        with col_e2:
            if disabled_eyes:
                loss_eyes_input = 0
                st.info("Глаза проигравших: 0")
            else:
                loss_eyes_input = st.number_input("Укажите глаза проигравших (0-11):", min_value=0, max_value=11, value=loss_eyes_val)
        
        if st.form_submit_button("СОХРАНИТЬ РЕЗУЛЬТАТ МАТЧА"):
            if match_password != "6666":
                st.error("🔒 Доступ отклонен! Неверный пароль.")
            elif gc is None:
                st.error("Ошибка синхронизации: база данных недоступна.")
            else:
                base_points = POINTS_DICT[status]
                win_pts = base_points + 1 if eggs else base_points
                loss_pts = 0
                
                try:
                    sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                    worksheet_g = sh.worksheet("games")
                    worksheet_g.append_row([
                        int(t1_actual), int(t2_actual), int(win_id_input),
                        int(win_pts), int(loss_pts), str(status), 
                        str(eggs).upper(), int(final_win_eyes), int(loss_eyes_input),
                        int(tour_to_save), float(time.time())
                    ])
                    st.success("Результат зафиксирован в Google Sheets!")
                    time.sleep(1.0)
                    force_reload()
                except Exception as e:
                    st.error(f"Критическая ошибка сохранения: {e}")

with col_bottom2:
    st.markdown("### 🛠️ Административная панель")
    
    with st.expander("❌ Удалить сыгранную игру по номеру строки", expanded=False):
        if st.session_state.games:
            game_numbers = list(range(1, len(st.session_state.games) + 1))
            selected_game_num = st.selectbox("Выберите порядковый номер записи для удаления:", game_numbers)
            g_idx = selected_game_num - 1
            game_info = st.session_state.games[g_idx]
            
            st.warning(f"Удаление: Тур {game_info.get('tour_number')} | Команда {game_info.get('team1_id')} vs Команда {game_info.get('team2_id')}")
            
            if st.button("УДАЛИТЬ ВЫБРАННЫЙ МАТЧ"):
                if match_password != "6666":
                    st.error("🔒 Введите корректный пароль администратора!")
                else:
                    try:
                        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                        worksheet_g = sh.worksheet("games")
                        worksheet_g.delete_rows(selected_game_num + 1)
                        st.success("Матч успешно аннулирован!")
                        time.sleep(1.0)
                        force_reload()
                    except Exception as e:
                        st.error(f"Ошибка удаления: {e}")
        else:
            st.info("В базе данных пока нет сохраненных матчей.")

    st.markdown("---")
    st.markdown("#### 🚨 Полный сброс результатов лиги")
    reset_password = st.text_input("🔑 Введите секретный ключ очистки:", type="password", key="r_pass")
    
    if st.button("🚨 УНИЧТОЖИТЬ ВСЕ ДАННЫЕ И ОБНУЛИТЬ"):
        if reset_password != "5559":
            st.error("🔒 Неверный секретный ключ доступа!")
        elif gc is None:
            st.error("Нет связи с облаком.")
        else:
            try:
                with st.spinner("Очистка таблиц Google Sheets..."):
                    sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                    worksheet_g = sh.worksheet("games")
                    row_count = len(worksheet_g.col_values(1))
                    if row_count > 1:
                        worksheet_g.resize(rows=1)
                        worksheet_g.resize(rows=100)
                        st.success("Все данные успешно стерты из облачной таблицы!")
                        time.sleep(1.5)
                        force_reload()
                    else:
                        st.info("Таблица уже пустая.")
            except Exception as e:
                st.error(f"Сбой сброса: {e}")
