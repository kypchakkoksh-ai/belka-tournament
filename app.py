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
    
    /* Контрастная желтая кнопка сохранения */
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
    
    /* Зеленые кнопки действий */
    div.stButton > button {
        background-color: #1e7e34 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    /* Красные кнопки удаления/исключения/сброса */
    button:contains("УДАЛИТЬ"), button:contains("Исключить"), button:contains("СБРОСИТЬ") {
        background-color: #b21f2d !important;
        color: #ffffff !important;
        border: 2px solid #dc3545 !important;
        font-weight: bold !important;
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

# Фиксированный список 10 игроков
DEFAULT_PLAYERS = ["Данияр", "Азирхан", "Талгат", "Елдар", "Марат", "Рустем", "Аманат", "Мерхат", "Шынгыс", "Ерлан"]

# НАДЁЖНАЯ ФУНКЦИЯ ЧТЕНИЯ ДАННЫХ
def load_fresh_data():
    if gc is None:
        return DEFAULT_PLAYERS.copy(), []
    try:
        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
        try:
            worksheet_p = sh.worksheet("players")
            players = [x for x in worksheet_p.col_values(1) if x and x != 'Имя']
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
    st.data_loaded = True

def force_reload():
    p_fresh, g_fresh = load_fresh_data()
    st.session_state.players = p_fresh
    st.session_state.games = g_fresh
    st.rerun()

# --- СИСТЕМА НАЧИСЛЕНИЯ ОЧКОВ (ГОЛЫЙ = 3 ОЧКА) ---
POINTS_DICT = {
    "Партия (3 очка)": 3,
    "Голый (3 очка)": 3,
    "Сокыр (12 очков)": 12
}

def calculate_match_points(status, eggs):
    base_points = POINTS_DICT[status]
    return (base_points + 1, 0) if eggs else (base_points, 0)


# --- ИНТЕРФЕЙС ---
st.title("🏆 ЛИГА БЕЛКИ — СИСТЕМА УЧЕТА ИГР")

if st.button("🔄 Синхронизировать с Google Таблицей"):
    force_reload()

st.markdown("---")

# --- СБОР СТАТИСТИКИ ---
global_stats = {p: {
    "Очки": 0, "Игры": 0, "Победы": 0, "Поражения": 0,
    "глаза_выигр": 0, "глаза_проигр": 0, "глаза_разница": 0,
    "партия_выигр": 0, "партия_проигр": 0, "партия_разница": 0,
    "голый_выигр": 0, "голый_проигр": 0, "голый_разница": 0,
    "яйца_выигр": 0, "яйца_проигр": 0, "яйца_разница": 0,
    "сокыр_выигр": 0, "сокыр_проигр": 0, "сокыр_разница": 0
} for p in st.session_state.players}

pairs_stats = {}

# Список для хранения сыгранных парных пар соперников для быстрой валидации дубликатов
played_matchups_db = {}

# Чтение и расчет статистики по всем играм
for idx, game in enumerate(st.session_state.games, start=1):
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

        # Сохраняем противостояние в базу сыгранных матчапов для валидации дубликатов
        team_a_set = frozenset(w_team)
        team_b_set = frozenset(l_team)
        matchup_key = frozenset([team_a_set, team_b_set])
        if matchup_key not in played_matchups_db:
            played_matchups_db[matchup_key] = idx

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

            if "Партия" in raw_status:
                global_stats[p]["партия_выигр"] += 1
                pairs_stats[win_pair]["[Партии] Выиграно"] += 1
            elif "Голый" in raw_status:
                global_stats[p]["голый_выигр"] += 1
                pairs_stats[win_pair]["[Голый] Выиграно"] += 1
            elif "Сокыр" in raw_status:
                global_stats[p]["сокыр_выигр"] += 1
                pairs_stats[win_pair]["[Сокыр] Выиграно"] += 1
            if is_eggs:
                global_stats[p]["яйца_выигр"] += 1
                pairs_stats[win_pair]["[Яйца] Повесили"] += 1
                
        for p in l_team:
            global_stats[p]["Очки"] += loss_pts
            global_stats[p]["Игры"] += 1
            global_stats[p]["Поражения"] += 1
            global_stats[p]["глаза_выигр"] += loss_eyes
            global_stats[p]["глаза_проигр"] += win_eyes

            if "Партия" in raw_status:
                global_stats[p]["партия_проигр"] += 1
                pairs_stats[loss_pair]["[Партии] Проиграно"] += 1
            elif "Голый" in raw_status:
                global_stats[p]["голый_проигр"] += 1
                pairs_stats[loss_pair]["[Голый] Проиграно"] += 1
            elif "Сокыр" in raw_status:
                global_stats[p]["сокыр_проигр"] += 1
                pairs_stats[loss_pair]["[Сокыр] Проиграно"] += 1
            if is_eggs:
                global_stats[p]["яйца_проигр"] += 1
                pairs_stats[loss_pair]["[Яйца] Получили"] += 1
    except:
        continue

for p in global_stats:
    global_stats[p]["глаза_разница"] = global_stats[p]["глаза_выигр"] - global_stats[p]["глаза_проигр"]
    for tag in ["партия", "голый", "яйца", "сокыр"]:
        global_stats[p][f"{tag}_разница"] = global_stats[p][f"{tag}_выигр"] - global_stats[p][f"{tag}_проигр"]


# --- 🏆 ГЛАВНАЯ ТУРНИРНАЯ ТАБЛИЦА (ГТТ) ---
st.markdown("### 🏆 Главная турнирная таблица")

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

st.markdown("---")


# --- РАЗДЕЛ АНАЛИТИКИ (ВКЛАДКИ) ---
st.markdown("### 📈 Детальная статистика и история")

tab_history, tab_partii, tab_glaza, tab_golye, tab_yaica, tab_sokyry, tab_pairs = st.tabs([
    "📜 История игр (Сыгранные матчи)", "🃏 Статистика Партий", "👁️ Глаза", "🔥 Голые", "🥚 Яйца", "🕶️ Сокыры", "👥 Рейтинг связок"
])

# ВКЛАДКА 1: ИСТОРИЯ ИГР
with tab_history:
    st.markdown("#### 📜 Все сыгранные матчи лиги (по порядку внесения)")
    if st.session_state.games:
        history_data = []
        for idx, game in enumerate(st.session_state.games, start=1):
            try:
                w_team = game.get("win_team", [])
                l_team = game.get("loss_team", [])
                win_eyes = game.get("win_eyes", 12)
                loss_eyes = game.get("loss_eyes", 0)
                status = game.get("status", "Партия")
                
                team_win_text = f"🟢 {w_team[0]} + {w_team[1]} ({win_eyes} гл.)"
                team_loss_text = f"🔴 {l_team[0]} + {l_team[1]} ({loss_eyes} гл.)"
                
                history_data.append({
                    "№": f"Матч {idx}",
                    "Победители": team_win_text,
                    "Проигравшие": team_loss_text,
                    "Тип победы / Статус": status
                })
            except:
                continue
        st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)
    else:
        st.info("В базе пока нет сыгранных матчей. Начните регистрацию ниже!")

# ДЕТАЛЬНЫЕ ВКЛАДКИ
with tab_partii:
    st.dataframe(df_leaderboard[["Игрок", "партия_выигр", "партия_проигр", "партия_разница"]].rename(
        columns={"партия_выигр": "Побед", "партия_проигр": "Проигрыш", "партия_разница": "Разница"}
    ).sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_glaza:
    st.dataframe(df_leaderboard[["Игрок", "глаза_выигр", "глаза_проигр", "глаза_разница"]].rename(
        columns={"глаза_выигр": "Набрано", "глаза_проигр": "Упущено", "глаза_разница": "Разница"}
    ).sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_golye:
    st.dataframe(df_leaderboard[["Игрок", "голый_выигр", "голый_проигр", "голый_разница"]].rename(
        columns={"голый_выигр": "Побед", "голый_проигр": "Проигрыш", "голый_разница": "Разница"}
    ).sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_yaica:
    st.dataframe(df_leaderboard[["Игрок", "яйца_выигр", "яйца_проигр", "яйца_разница"]].rename(
        columns={"яйца_выигр": "Повесили", "яйца_проигр": "Получили", "яйца_разница": "Разница"}
    ).sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

with tab_sokyry:
    st.dataframe(df_leaderboard[["Игрок", "сокыр_выигр", "сокыр_проигр", "сокыр_разница"]].rename(
        columns={"сокыр_выигр": "Побед", "сокыр_проигр": "Проигрыш", "сокыр_разница": "Разница"}
    ).sort_values(by="Разница", ascending=False), use_container_width=True, hide_index=True)

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
        status = st.selectbox("Как завершилась игра?", ["Партия (3 очка)", "Голый (3 очка)", "Сокыр (12 очков)"])
        eggs = st.checkbox("Повесили «Яйца» (+1 очко победителю)")

        # Логика интерактивного выбора глаз
        if status == "Голый (3 очка)":
            disabled_eyes = True
            default_win_eyes = 12
            default_loss_eyes = 0
        else:
            disabled_eyes = False
            default_win_eyes = 12
            default_loss_eyes = 4

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if disabled_eyes:
                final_win_eyes = 12
                st.info("Глаза Победителей: 12 (Голый)")
            else:
                # В случае "Яиц" победители могут набрать и больше, разрешим ввод 12-16
                final_win_eyes = st.number_input("Глаза Победителей (12-16)", min_value=12, max_value=16, value=default_win_eyes + (1 if eggs else 0), step=1)
        with col_e2:
            if disabled_eyes:
                loss_eyes_input = 0
                st.info("Глаза Проигравших: 0 (Голый)")
            else:
                loss_eyes_input = st.number_input("Глаза Проигравших (0-11)", min_value=0, max_value=11, value=default_loss_eyes, step=1)
        
        if st.form_submit_button("СОХРАНИТЬ РЕЗУЛЬТАТ"):
            # 1. Проверка пароля
            if match_password != "6666":
                st.error("🔒 Неверный пароль!")
            # 2. Проверка дублирования игроков внутри формы
            elif len({p1, p2, p3, p4}) < 4:
                st.error("Ошибка: Один и тот же игрок выбран на разных позициях!")
            elif gc is None:
                st.error("Ошибка подключения к Google Таблицам.")
            else:
                # 3. ВАЛИДАЦИЯ ПОВТОРНОГО МАТЧА (Дубликат пар соперников)
                form_team_win = frozenset([p1, p2])
                form_team_loss = frozenset([p3, p4])
                form_matchup_key = frozenset([form_team_win, form_team_loss])
                
                if form_matchup_key in played_matchups_db:
                    duplicate_match_id = played_matchups_db[form_matchup_key]
                    st.error(
                        f"🛑 Регистрация невозможна! "
                        f"Состав участников {p1}+{p2} против {p3}+{p4} уже сыграл ранее в **Матче №{duplicate_match_id}**."
                    )
                else:
                    # Если проверки пройдены — сохраняем результат
                    win_pts, loss_pts = calculate_match_points(status, eggs)
                    try:
                        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                        worksheet_g = sh.worksheet("games")
                        worksheet_g.append_row([
                            f"{p1}, {p2}", f"{p3}, {p4}", int(win_pts), int(loss_pts),
                            str(status), str(eggs).upper(), f"{status} {'+ Яйца' if eggs else ''}",
                            float(time.time()), int(final_win_eyes), int(loss_eyes_input)
                        ])
                        st.success("Результат занесен в облако!")
                        time.sleep(1.0)
                        force_reload()
                    except Exception as e:
                        st.error(f"Ошибка сохранения: {e}")

    st.markdown("### 🛠️ Корректировка результатов")
    with st.expander("❌ Удалить конкретную игру по номеру", expanded=False):
        if st.session_state.games:
            game_numbers = list(range(1, len(st.session_state.games) + 1))
            selected_game_num = st.selectbox("Выберите номер матча для удаления:", game_numbers)
            game_info = st.session_state.games[selected_game_num - 1]
            st.info(f"**Матч №{selected_game_num}:** Победители: {', '.join(game_info['win_team'])} | Проигравшие: {', '.join(game_info['loss_team'])}")
            
            if st.button("УДАЛИТЬ ВЫБРАННЫЙ МАТЧ"):
                if match_password != "6666": st.error("🔒 Введите пароль администратора!")
                else:
                    try:
                        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                        worksheet_g = sh.worksheet("games")
                        worksheet_g.delete_rows(selected_game_num + 1)
                        st.success("Матч удален!")
                        time.sleep(1.0)
                        force_reload()
                    except Exception as e: st.error(f"Ошибка удаления: {e}")
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
        if reset_password != "5559": st.error("🔒 Доступ заблокирован!")
        else:
            try:
                sh = gc.open_by_url(st.secrets["spreadsheet_url"])
                worksheet_g = sh.worksheet("games")
                if len(worksheet_g.col_values(1)) > 1:
                    worksheet_g.resize(rows=1)
                    worksheet_g.resize(rows=100)
                    st.success("Данные успешно стерты!")
                    time.sleep(1.5)
                    force_reload()
            except Exception as e: st.error(f"Сбой при очистке: {e}")
