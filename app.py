import streamlit as st
import pandas as pd
import json
import os
import time

# Настройка страницы: дефолтный dark mode и заголовок
st.set_page_config(page_title="Чемпионат по Белке", layout="wide", page_icon="🃏")

# --- СТИЛИЗАЦИЯ И ИНТЕРФЕЙС (Зеленое сукно, адаптивность, исправление цвета текста) ---
st.markdown("""
    <style>
    /* Настройка главного фона - благородный темно-зеленый */
    .stApp {
        background-color: #0b3017;
        background-image: radial-gradient(circle, #0e4220 0%, #071f0e 100%);
        color: #f0f2f6;
    }
    
    /* Делаем подписи к полям ввода (Победитель 1, Пароль и т.д.) ярко-белыми */
    .stWidgetFormLabel, label, [data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 14px !important;
    }
    
    /* Стилизация чекбоксов (текст рядом с галочкой "Повесили Яйца") */
    [data-testid="stCheckbox"] label p {
        color: #ffffff !important;
    }
    
    /* Стилизация карточек и блоков для читаемости на мобильных */
    div.stButton > button {
        width: 100% !important;
        background-color: #1e7e34 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: 1px solid #28a745 !important;
        padding: 0.5rem 1rem !important;
    }
    div.stButton > button:hover {
        background-color: #218838 !important;
        border-color: #1e7e34 !important;
    }
    
    /* Делаем вкладки (Tabs) крупными и удобными для пальцев на телефоне */
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: bold !important;
        padding: 12px 16px !important;
        color: #a3cfbb !important;
    }
    button[aria-selected="true"] {
        color: #ffffff !important;
        border-bottom-color: #28a745 !important;
    }
    
    /* Красивые кастомные контейнеры для форм */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
    }
    
    /* Стилизация разделителей */
    hr {
        border-top: 1px solid #1e7e34 !important;
    }
    </style>
""", unsafe_allow_html=True)

PLAYERS_FILE = "belka_players.json"
GAMES_FILE = "belka_games.json"

def load_data():
    if os.path.exists(PLAYERS_FILE):
        try:
            with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
                st.session_state.players = json.load(f)
        except Exception:
            st.session_state.players = ["Данияр", "Азирхан", "Талгат", "Елдар", "Марат", "Рустем", "Ерлан", "Каиржан", "Аманат", "Мирхат", "Шынгыс"]
    else:
        st.session_state.players = ["Данияр", "Азирхан", "Талгат", "Елдар", "Марат", "Рустем", "Ерлан", "Каиржан", "Аманат", "Мирхат", "Шынгыс"]
        
    if os.path.exists(GAMES_FILE):
        try:
            with open(GAMES_FILE, "r", encoding="utf-8") as f:
                st.session_state.games = json.load(f)
        except Exception:
            st.session_state.games = []
    else:
        st.session_state.games = []

def save_players():
    with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.players, f, ensure_ascii=False, indent=4)

def save_games():
    with open(GAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.games, f, ensure_ascii=False, indent=4)

load_data()

POINTS_DICT = {
    "Сокыр (24 очка)": 24,
    "Теке (6 очков)": 6,
    "Голый (3 очка)": 3,
    "Обычная игра (0 очков)": 0
}

def calculate_match_points(status, eggs):
    base_points = POINTS_DICT[status]
    additional = 2 if eggs else 0
    return base_points + additional, 0

# --- СБОР РАСШИРЕННОЙ СТАТИСТИКИ ---
stats = {
    player: {
        "Очки": 0, "Игры": 0, "Средний балл": 0.0, 
        "Выигр. Сокыр": 0, "Проигр. Сокыр": 0,
        "Выигр. Теке": 0, "Проигр. Теке": 0,
        "Выигр. Голый": 0, "Проигр. Голый": 0,
        "Выигр. Яйца": 0, "Проигр. Яйца": 0
    } for player in st.session_state.players
}
pairs_stats = {}

for game in st.session_state.games:
    win_pair = tuple(sorted(game["win_team"]))
    if win_pair not in pairs_stats: pairs_stats[win_pair] = {"Очки": 0, "Игры": 0}
    pairs_stats[win_pair]["Очки"] += game["win_points"]
    pairs_stats[win_pair]["Игры"] += 1

    for p in game["win_team"]:
        if p in stats:
            stats[p]["Очки"] += game["win_points"]
            stats[p]["Игры"] += 1
            if "Сокыр" in game["raw_status"]: stats[p]["Выигр. Сокыр"] += 1
            elif "Теке" in game["raw_status"]: stats[p]["Выигр. Теке"] += 1
            elif "Голый" in game["raw_status"]: stats[p]["Выигр. Голый"] += 1
            if game.get("eggs_happened", False): stats[p]["Выигр. Яйца"] += 1
            
    for p in game["loss_team"]:
        if p in stats: 
            stats[p]["Игры"] += 1
            if "Сокыр" in game["raw_status"]: stats[p]["Проигр. Сокыр"] += 1
            elif "Теке" in game["raw_status"]: stats[p]["Проигр. Теке"] += 1
            elif "Голый" in game["raw_status"]: stats[p]["Проигр. Голый"] += 1
            if game.get("eggs_happened", False): stats[p]["Проигр. Яйца"] += 1

for player in stats:
    if stats[player]["Игры"] > 0:
        stats[player]["Средний балл"] = round(stats[player]["Очки"] / stats[player]["Игры"], 2)

df_leaderboard = pd.DataFrame.from_dict(stats, orient='index').reset_index()
df_leaderboard.columns = [
    "Игрок", "Всего очков", "Сыграно игр", "Средний балл", 
    "Выигр. Сокыр", "Проигр. Сокыр", 
    "Выигр. Теке", "Проигр. Теке", 
    "Выигр. Голый", "Проигр. Голый",
    "Повесили Яйца", "Получили Яйца"
]

# === ПОРЯДОК ЭЛЕМЕНТОВ ===

# 1. Шапка сайта и кнопка обновления
st.title("🃏 Чемпионат по Белке")
if st.button("🔄 Обновить данные"):
    load_data()
    st.rerun()

# 2. ГЛАВНАЯ ТАБЛИЦА
st.markdown("### 🏆 Главная турнирная таблица")
df_main = df_leaderboard.sort_values(by=["Всего очков", "Средний балл"], ascending=[False, False]).reset_index(drop=True)
df_main.index = df_main.index + 1
st.dataframe(df_main, use_container_width=True)

st.markdown("---")

# 3. ДОПОЛНИТЕЛЬНАЯ АНАЛИТИКА
st.markdown("### 📊 Дополнительная аналитика")
tab_history, tab_positive, tab_negative, tab_pairs = st.tabs([
    "📝 История всех игр", 
    "🚀 Положительный рейтинг", 
    "📉 Отрицательный рейтинг", 
    "👥 Результативность пар"
])

# Вкладка 1: История всех игр
with tab_history:
    st.markdown("#### История сыгранных матчей")
    if st.session_state.games:
        log_data = []
        indexed_games = list(enumerate(st.session_state.games, 1))
        sorted_games = sorted(indexed_games, key=lambda x: x[1].get('timestamp', 0), reverse=True)
        for original_num, g in sorted_games:
            log_data.append({
                "Матч №": original_num, 
                "Победители": f"{g['win_team'][0]}, {g['win_team'][1]}", 
                "Проигравшие": f"{g['loss_team'][0]}, {g['loss_team'][1]}", 
                "Что произошло": g["status"], 
                "Очки": f"+{g['win_points']}"
            })
        st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)
    else:
        st.info("Игр еще не было.")

# Вкладка 2: Положительный рейтинг
with tab_positive:
    st.markdown("#### Кто чаще раздавал особые статусы")
    sub_p1, sub_p2, sub_p3, sub_p4 = st.tabs(["🔥 Сокыры", "🐐 Теке", "🪵 Голые", "🥚 Яйца"])
    
    with sub_p1:
        df_p1 = df_leaderboard[["Игрок", "Выигр. Сокыр"]].sort_values(by="Выигр. Сокыр", ascending=False).reset_index(drop=True)
        df_p1.index = df_p1.index + 1
        st.dataframe(df_p1, use_container_width=True)
    with sub_p2:
        df_p2 = df_leaderboard[["Игрок", "Выигр. Теке"]].sort_values(by="Voice. Теке", ascending=False, errors='ignore').reset_index(drop=True)
        if "Выигр. Теке" in df_leaderboard.columns:
            df_p2 = df_leaderboard[["Игрок", "Выигр. Теке"]].sort_values(by="Выигр. Теке", ascending=False).reset_index(drop=True)
        df_p2.index = df_p2.index + 1
        st.dataframe(df_p2, use_container_width=True)
    with sub_p3:
        df_p3 = df_leaderboard[["Игрок", "Выигр. Голый"]].sort_values(by="Выигр. Голый", ascending=False).reset_index(drop=True)
        df_p3.index = df_p3.index + 1
        st.dataframe(df_p3, use_container_width=True)
    with sub_p4:
        df_p4 = df_leaderboard[["Игрок", "Повесили Яйца"]].sort_values(by="Повесили Яйца", ascending=False).reset_index(drop=True)
        df_p4.index = df_p4.index + 1
        st.dataframe(df_p4, use_container_width=True)

# Вкладка 3: Отрицательный рейтинг
with tab_negative:
    st.markdown("#### Кто чаще ловил раздачи")
    sub_n1, sub_n2, sub_n3, sub_n4 = st.tabs(["👁️ Сокыры", "🐐 Теке", "🪵 Голые", "🥚 Яйца"])
    
    with sub_n1:
        df_n1 = df_leaderboard[["Игрок", "Проигр. Сокыр"]].sort_values(by="Проигр. Сокыр", ascending=False).reset_index(drop=True)
        df_n1.index = df_n1.index + 1
        st.dataframe(df_n1, use_container_width=True)
    with sub_n2:
        df_n2 = df_leaderboard[["Игрок", "Проигр. Теке"]].sort_values(by="Проигр. Теке", ascending=False).reset_index(drop=True)
        df_n2.index = df_n2.index + 1
        st.dataframe(df_n2, use_container_width=True)
    with sub_n3:
        df_n3 = df_leaderboard[["Игрок", "Проигр. Голый"]].sort_values(by="Проигр. Голый", ascending=False).reset_index(drop=True)
        df_n3.index = df_n3.index + 1
        st.dataframe(df_n3, use_container_width=True)
    with sub_n4:
        df_n4 = df_leaderboard[["Игрок", "Получили Яйца"]].sort_values(by="Получили Яйца", ascending=False).reset_index(drop=True)
        df_n4.index = df_n4.index + 1
        st.dataframe(df_n4, use_container_width=True)

# Вкладка 4: Результативность пар
with tab_pairs:
    st.markdown("#### Рейтинг связок")
    if pairs_stats:
        pairs_list = [{"Пара игроков": f"{k[0]} 🤝 {k[1]}", "Очки": v["Очки"], "Игры": v["Игры"], "Средний балл": round(v["Очки"] / v["Игры"], 2)} for k, v in pairs_stats.items()]
        df_p = pd.DataFrame(pairs_list).sort_values(by=["Очки", "Средний балл"], ascending=[False, False]).reset_index(drop=True)
        df_p.index = df_p.index + 1
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("Матчей пока нет.")

st.markdown("---")

# 4. ФОРМЫ УПРАВЛЕНИЯ ВНИЗУ
col_bottom1, col_bottom2 = st.columns([1, 1])

with col_bottom1:
    st.markdown("### ➕ Регистрация игры")
    match_password = st.text_input("🔑 Пароль (Ввод / Правка):", type="password")
    
    with st.form("match_form", clear_on_submit=False):
        p1 = st.selectbox("Победитель 1", st.session_state.players, index=0 if len(st.session_state.players) > 0 else None)
        p2 = st.selectbox("Победитель 2", st.session_state.players, index=1 if len(st.session_state.players) > 1 else None)
        p3 = st.selectbox("Проигравший 1", st.session_state.players, index=2 if len(st.session_state.players) > 2 else None)
        p4 = st.selectbox("Проигравший 2", st.session_state.players, index=3 if len(st.session_state.players) > 3 else None)
        status = st.selectbox("Что дали победители?", list(POINTS_DICT.keys()))
        eggs = st.checkbox("Повесили «Яйца» (+2 очка)")
        
        if st.form_submit_button("СОХРАНИТЬ РЕЗУЛЬТАТ"):
            if match_password != "6666":
                st.error("🔒 Неверный пароль!")
            elif len({p1, p2, p3, p4}) < 4:
                st.error("Ошибка: Игроки дублируются!")
            else:
                load_data()
                win_pts, loss_pts = calculate_match_points(status, eggs)
                st.session_state.games.append({
                    "win_team": [p1, p2], "loss_team": [p3, p4],
                    "win_points": win_pts, "loss_points": loss_pts,
                    "raw_status": status, "eggs_happened": eggs,
                    "status": f"{status} {'+ Яйца' if eggs else ''}", "timestamp": time.time()
                })
                save_games()
                st.success("Сохранено!")
                st.rerun()

with col_bottom2:
    st.markdown("### ✏️ Корректировка прошедших матчей")
    with st.expander("Открыть панель редактирования"):
        if not st.session_state.games:
            st.info("История пуста.")
        else:
            match_indices = list(range(1, len(st.session_state.games) + 1))
            selected_match_num = st.selectbox("Выберите № матча:", match_indices)
            target_idx = selected_match_num - 1
            current_match = st.session_state.games[target_idx]
            
            st.caption(f"Сейчас: {current_match['win_team'][0]}/{current_match['win_team'][1]} обыграли {current_match['loss_team'][0]}/{current_match['loss_team'][1]} ({current_match['status']})")
            
            edit_p1 = st.selectbox("Новый Поб-1", st.session_state.players, index=st.session_state.players.index(current_match['win_team'][0]) if current_match['win_team'][0] in st.session_state.players else 0)
            edit_p2 = st.selectbox("Новый Поб-2", st.session_state.players, index=st.session_state.players.index(current_match['win_team'][1]) if current_match['win_team'][1] in st.session_state.players else 1)
            edit_p3 = st.selectbox("Новый Проиг-1", st.session_state.players, index=st.session_state.players.index(current_match['loss_team'][0]) if current_match['loss_team'][0] in st.session_state.players else 2)
            edit_p4 = st.selectbox("Новый Проиг-2", st.session_state.players, index=st.session_state.players.index(current_match['loss_team'][1]) if current_match['loss_team'][1] in st.session_state.players else 3)
            edit_status = st.selectbox("Новый исход", list(POINTS_DICT.keys()), index=list(POINTS_DICT.keys()).index(current_match['raw_status']) if current_match['raw_status'] in POINTS_DICT else 0)
            edit_eggs = st.checkbox("Были Яйца", value=current_match.get("eggs_happened", False), key="edit_eg_ch")
            
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("💾 Изменить"):
                    if match_password != "6666": st.error("Пароль!")
                    elif len({edit_p1, edit_p2, edit_p3, edit_p4}) < 4: st.error("Дубли!")
                    else:
                        load_data()
                        w_pts, _ = calculate_match_points(edit_status, edit_eggs)
                        st.session_state.games[target_idx] = {
                            "win_team": [edit_p1, edit_p2], "loss_team": [edit_p3, edit_p4],
                            "win_points": w_pts, "loss_points": 0, "raw_status": edit_status,
                            "eggs_happened": edit_eggs, "status": f"{edit_status} {'+ Яйца' if edit_eggs else ''}",
                            "timestamp": current_match.get('timestamp', time.time())
                        }
                        save_games()
                        st.success("Изменено!")
                        st.rerun()
            with cb2:
                if st.button("🗑️ Удалить матч"):
                    if match_password != "6666": st.error("Пароль!")
                    else:
                        load_data()
                        st.session_state.games.pop(target_idx)
                        save_games()
                        st.warning("Удалено!")
                        st.rerun()

st.markdown("---")

# 5. УПРАВЛЕНИЕ СОСТАВОМ В САМОМ НИЗУ
st.markdown("### ⚙️ Управление составом игроков")
col_p1, col_p2 = st.columns(2)
with col_p1:
    with st.expander("➕ Добавить игрока"):
        new_player = st.text_input("Имя:")
        if st.button("Зарегистрировать"):
            load_data()
            if new_player.strip() and new_player.strip() not in st.session_state.players:
                st.session_state.players.append(new_player.strip())
                save_players()
                st.success("Добавлен!")
                st.rerun()
with col_p2:
    with st.expander("❌ Удалить игрока"):
        player_to_remove = st.selectbox("Кого удалить:", st.session_state.players)
        if st.button("Удалить навсегда"):
            load_data()
            st.session_state.players.remove(player_to_remove)
            save_players()
            st.warning("Удален!")
            st.rerun()
