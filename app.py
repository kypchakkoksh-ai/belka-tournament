import streamlit as st
import pandas as pd
import gspread
import time

# Настройка страницы
st.set_page_config(page_title="Чемпионат по Белке", layout="wide", page_icon="🃏")

# --- СТИЛИЗАЦИЯ И ИНТЕРФЕЙС (Зеленое сукно + Контрастная Желтая Кнопка) ---
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
    [data-testid="stCheckbox"] label p { color: #ffffff !important; }
    
    /* Мощная Желтая кнопка сохранения с черным жирным текстом */
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
    
    /* Стандартные кнопки действия (зеленые) */
    div.stButton > button {
        background-color: #1e7e34 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    /* Красные кнопки для опасных удалений */
    button:contains("УДАЛИТЬ") {
        background-color: #b21f2d !important;
        color: #ffffff !important;
        border: 2px solid #dc3545 !important;
    }
    
    button[data-baseweb="tab"] { font-size: 15px !important; font-weight: bold !important; color: #a3cfbb !important; }
    button[aria-selected="true"] { color: #ffffff !important; border-bottom-color: #28a745 !important; }
    hr { border-top: 1px solid #1e7e34 !important; }
    </style>
""", unsafe_allow_html=True)

# Инициализация подключения через gspread и Secrets
@st.cache_resource
def get_gspread_client():
    try:
        credentials = dict(st.secrets["gcp_service_account"])
        if "private_key" in credentials:
            credentials["private_key"] = credentials["private_key"].replace("\\n", "\n")
        gc = gspread.service_account_from_dict(credentials)
        return gc
    except Exception as e:
        st.error(f"Ошибка авторизации Google Ключа: {e}")
        return None

gc = get_gspread_client()

DEFAULT_PLAYERS = ["Данияр", "Азирхан", "Талгат", "Елдар", "Марат", "Рустем", "Ерлан", "Каиржан", "Аманат", "Мирхат", "Шынгыс"]

@st.cache_data(ttl=2)
def load_data_from_sheets():
    if gc is None:
        return DEFAULT_PLAYERS.copy(), []
    try:
        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
        
        # Загрузка игроков
        try:
            worksheet_p = sh.worksheet("players")
            records_p = worksheet_p.get_all_records()
            if records_p and 'Имя' in records_p[0]:
                df_p = pd.DataFrame(records_p)
                players = df_p['Имя'].dropna().astype(str).tolist()
            else:
                players = [x for x in worksheet_p.col_values(1) if x and x != 'Имя']
            if not players: players = DEFAULT_PLAYERS.copy()
        except:
            players = DEFAULT_PLAYERS.copy()
            
        # Загрузка матчей
        try:
            worksheet_g = sh.worksheet("games")
            df_g = pd.DataFrame(worksheet_g.get_all_records())
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
        return DEFAULT_PLAYERS.copy(), []

# Загрузка актуальных данных
st.session_state.players, st.session_state.games = load_data_from_sheets()

POINTS_DICT = {
    "Сокыр (24 очка)": 24, "Теке (6 очков)": 6, "Голый (3 очка)": 3, "Обычная игра (0 очков)": 0
}

def calculate_match_points(status, eggs):
    base_points = POINTS_DICT[status]
    return (base_points + 2, 0) if eggs else (base_points, 0)

# --- РАСЧЕТ СТАТИСТИКИ ---
stats = {p: {
    "Очки": 0, "Игры": 0, "Средний балл": 0.0, 
    "Выигр. Сокыр": 0, "Проигр. Сокыр": 0, 
    "Выигр. Теке": 0, "Проигр. Теке": 0, 
    "Выигр. Голый": 0, "Проигр. Голый": 0, 
    "Выигр. Яйца": 0, "Проигр. Яйца": 0
} for p in st.session_state.players}

pairs_stats = {}

for game in st.session_state.games:
    try:
        w_team = game.get("win_team", [])
        l_team = game.get("loss_team", [])
        if len(w_team) < 2 or len(l_team) < 2: continue
        
        win_pair = tuple(sorted(w_team))
        if win_pair not in pairs_stats: pairs_stats[win_pair] = {"Очки": 0, "Игры": 0}
        pairs_stats[win_pair]["Очки"] += int(game.get("win_points", 0))
        pairs_stats[win_pair]["Игры"] += 1

        raw_status = str(game.get("raw_status", ""))
        is_eggs = str(game.get("eggs_happened", "")).upper() in ["TRUE", "1", "ИСТИНА"]

        for p in w_team:
            if p in stats:
                stats[p]["Очки"] += int(game.get("win_points", 0))
                stats[p]["Игры"] += 1
                if "Сокыр" in raw_status: stats[p]["Выигр. Сокыр"] += 1
                elif "Теке" in raw_status: stats[p]["Выигр. Теке"] += 1
                elif "Голый" in raw_status: stats[p]["Выигр. Голый"] += 1
                if is_eggs: stats[p]["Выигр. Яйца"] += 1
                
        for p in l_team:
            if p in stats:
                stats[p]["Игры"] += 1
                if "Сокыр" in raw_status: stats[p]["Проигр. Сокыр"] += 1
                elif "Теке" in raw_status: stats[p]["Проигр. Теке"] += 1
                elif "Голый" in raw_status: stats[p]["Проигр. Голый"] += 1
                if is_eggs: stats[p]["Проигр. Яйца"] += 1
    except:
        continue

for p in stats:
    if stats[p]["Игры"] > 0:
        stats[p]["Средний балл"] = round(stats[p]["Очки"] / stats[p]["Игры"], 2)

df_leaderboard = pd.DataFrame.from_dict(stats, orient='index').reset_index()
df_leaderboard.columns = ["Игрок", "Всего очков", "Сыграно игр", "Средний балл", "Выигр. Сокыр", "Проигр. Сокыр", "Выигр. Теке", "Проигр. Теке", "Выигр. Голый", "Проигр. Голый", "Повесили Яйца", "Получили Яйца"]

# === ЭЛЕМЕНТЫ ИНТЕРФЕЙСА ===
st.title("🃏 Чемпионат по Белке")
if st.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()

st.markdown("### 🏆 Главная турнирная таблица")
df_main = df_leaderboard.sort_values(by=["Всего очков", "Средний балл"], ascending=[False, False]).reset_index(drop=True)
df_main.index = df_main.index + 1
st.dataframe(df_main, use_container_width=True)

st.markdown("---")

# Вкладки доп. аналитики
tab_history, tab_positive, tab_negative, tab_pairs = st.tabs([
    "📝 История игр", "🚀 Раздали (Выигрыши)", "📉 Словленные (Проигрыши)", "👥 Рейтинг связок"
])

with tab_history:
    if st.session_state.games:
        log_data = [{"Матч №": i, "Победители": f"{g['win_team'][0]}, {g['win_team'][1]}", "Проигравшие": f"{g['loss_team'][0]}, {g['loss_team'][1]}", "Статус": g.get("status"), "Очки": f"+{g['win_points']}"} for i, g in enumerate(st.session_state.games, 1)]
        st.dataframe(pd.DataFrame(log_data)[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("История пуста.")

with tab_positive:
    st.markdown("#### Подробная статистика победных достижений")
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["👁️ Сокыр", "🐐 Теке", "🪵 Голый", "🥚 Повесили Яйца"])
    
    with sub_tab1:
        df_p1 = df_leaderboard[["Игрок", "Выигр. Сокыр"]].sort_values(by="Выигр. Сокыр", ascending=False).reset_index(drop=True)
        df_p1.index = df_p1.index + 1
        st.dataframe(df_p1, use_container_width=True)
    with sub_tab2:
        df_p2 = df_leaderboard[["Игрок", "Выигр. Теке"]].sort_values(by="Выигр. Теке", ascending=False).reset_index(drop=True)
        df_p2.index = df_p2.index + 1
        st.dataframe(df_p2, use_container_width=True)
    with sub_tab3:
        df_p3 = df_leaderboard[["Игрок", "Выигр. Голый"]].sort_values(by="Выигр. Голый", ascending=False).reset_index(drop=True)
        df_p3.index = df_p3.index + 1
        st.dataframe(df_p3, use_container_width=True)
    with sub_tab4:
        df_p4 = df_leaderboard[["Игрок", "Повесили Яйца"]].sort_values(by="Повесили Яйца", ascending=False).reset_index(drop=True)
        df_p4.index = df_p4.index + 1
        st.dataframe(df_p4, use_container_width=True)

with tab_negative:
    st.markdown("#### Подробная статистика по проигранным сдачам")
    sub_neg1, sub_neg2, sub_neg3, sub_neg4 = st.tabs(["👁️ Словлен Сокыр", "🐐 Словлен Теке", "🪵 Словлен Голый", "🥚 Получили Яйца"])
    
    with sub_neg1:
        df_n1 = df_leaderboard[["Игрок", "Проигр. Сокыр"]].sort_values(by="Проигр. Сокыр", ascending=False).reset_index(drop=True)
        df_n1.index = df_n1.index + 1
        st.dataframe(df_n1, use_container_width=True)
    with sub_neg2:
        df_n2 = df_leaderboard[["Игрок", "Проигр. Теке"]].sort_values(by="Проигр. Теке", ascending=False).reset_index(drop=True)
        df_n2.index = df_n2.index + 1
        st.dataframe(df_n2, use_container_width=True)
    with sub_neg3:
        df_n3 = df_leaderboard[["Игрок", "Проигр. Голый"]].sort_values(by="Проигр. Голый", ascending=False).reset_index(drop=True)
        df_n3.index = df_n3.index + 1
        st.dataframe(df_n3, use_container_width=True)
    with sub_neg4:
        df_n4 = df_leaderboard[["Игрок", "Получили Яйца"]].sort_values(by="Получили Яйца", ascending=False).reset_index(drop=True)
        df_n4.index = df_n4.index + 1
        st.dataframe(df_n4, use_container_width=True)

with tab_pairs:
    if pairs_stats:
        p_list = [{"Пара игроков": f"{k[0]} 🤝 {k[1]}", "Очки": v["Очки"], "Игры": v["Игры"], "Средний балл": round(v["Очки"] / v["Игры"] if v["Игры"]>0 else 0, 2)} for k, v in pairs_stats.items()]
        df_p_sorted = pd.DataFrame(p_list).sort_values(by=["Очки", "Средний балл"], ascending=[False, False]).reset_index(drop=True)
        df_p_sorted.index = df_p_sorted.index + 1
        st.dataframe(df_p_sorted, use_container_width=True)
    else:
        st.info("Матчей пар пока нет.")

st.markdown("---")

col_bottom1, col_bottom2 = st.columns([1, 1])

with col_bottom1:
    st.markdown("### ➕ Регистрация игры")
    match_password = st.text_input("🔑 Пароль администратора:", type="password")

    with st.form("match_form", clear_on_submit=True):
        p1 = st.selectbox("Победитель 1", st.session_state.players, index=0)
        p2 = st.selectbox("Победитель 2", st.session_state.players, index=1)
        p3 = st.selectbox("Проигравший 1", st.session_state.players, index=2)
        p4 = st.selectbox("Проигравший 2", st.session_state.players, index=3)
        status = st.selectbox("Что дали?", list(POINTS_DICT.keys()))
        eggs = st.checkbox("Повесили «Яйца» (+2 очка)")
        
        # Кнопка теперь сочно-желтая с жирным черным шрифтом
        if st.form_submit_button("СОХРАНИТЬ РЕЗУЛЬТАТ"):
            if match_password != "6666":
                st.error("🔒 Неверный пароль!")
            elif len({p1, p2, p3, p4}) < 4:
                st.error("Ошибка: Участники дублируются!")
            elif gc is None:
                st.error("Ошибка: Подключение не настроено.")
            else:
                win_pts, loss_pts = calculate_match_points(status, eggs)
                try:
                    sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                    worksheet_g = sh.worksheet("games")
                    worksheet_g.append_row([
                        f"{p1}, {p2}", f"{p3}, {p4}", int(win_pts), int(loss_pts),
                        str(status), str(eggs).upper(), f"{status} {'+ Яйца' if eggs else ''}", float(time.time())
                    ])
                    st.success("Результат успешно сохранен в Облаке!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка сохранения: {e}")

    # --- УЛУЧШЕННАЯ КОРРЕКТИРОВКА ЛЮБОЙ ИГРЫ ---
    st.markdown("### 🛠️ Корректировка игр")
    with st.expander("❌ Удалить конкретную игру по номеру", expanded=False):
        if st.session_state.games:
            game_numbers = list(range(1, len(st.session_state.games) + 1))
            selected_game_num = st.selectbox("Выберите номер матча для удаления из истории:", game_numbers)
            
            # Показываем инфо о выбранном матче для проверки
            g_idx = selected_game_num - 1
            game_info = st.session_state.games[g_idx]
            st.info(f"**Матч №{selected_game_num}:** Победители: {', '.join(game_info['win_team'])} | Проигравшие: {', '.join(game_info['loss_team'])} | Статус: {game_info.get('status')}")
            
            if st.button("УДАЛИТЬ ВЫБРАННЫЙ МАТЧ"):
                if match_password != "6666":
                    st.error("🔒 Введите пароль администратора выше!")
                elif gc is None:
                    st.error("Нет подключения к Google Таблицам.")
                else:
                    try:
                        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                        worksheet_g = sh.worksheet("games")
                        # Индекс строки в таблице с учетом шапки (строка 1 - шапка, значит матч №1 - это строка 2)
                        row_to_delete = selected_game_num + 1
                        worksheet_g.delete_rows(row_to_delete)
                        
                        st.success(f"Матч №{selected_game_num} успешно стерт из базы!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка при удалении строки: {e}")
        else:
            st.info("История матчей пуста, удалять нечего.")

with col_bottom2:
    st.markdown("### ⚙️ Управление составом")
    
    # Добавление игрока
    with st.expander("➕ Добавить нового игрока в облако", expanded=True):
        new_player = st.text_input("Имя нового участника:")
        if st.button("ДОБАВИТЬ В БАЗУ"):
            if match_password != "6666":
                st.error("🔒 Введите верный пароль выше!")
            elif gc is None:
                st.error("Нет подключения к Google Таблицам.")
            elif new_player.strip():
                try:
                    sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                    worksheet_p = sh.worksheet("players")
                    worksheet_p.append_row([new_player.strip()])
                    st.success(f"Игрок {new_player} успешно добавлен!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка добавления: {e}")

    # Удаление игрока
    with st.expander("🗑️ Удалить игрока из базы", expanded=False):
        player_to_delete = st.selectbox("Выберите игрока для удаления", st.session_state.players)
        if st.button("🚨 УДАЛИТЬ ИГРОКА ИЗ СИСТЕМЫ"):
            if match_password != "6666":
                st.error("🔒 Введите верный пароль выше!")
            elif gc is None:
                st.error("Нет подключения к Google Таблицам.")
            else:
                try:
                    sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                    worksheet_p = sh.worksheet("players")
                    col_values = worksheet_p.col_values(1)
                    
                    if player_to_delete in col_values:
                        row_idx = col_values.index(player_to_delete) + 1
                        worksheet_p.delete_rows(row_idx)
                        st.success(f"Игрок {player_to_delete} успешно удален из базы!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Игрок не найден в таблице.")
                except Exception as e:
                    st.error(f"Ошибка удаления: {e}")
