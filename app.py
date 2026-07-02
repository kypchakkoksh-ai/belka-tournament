import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

# Настройка страницы
st.set_page_config(page_title="Чемпионат по Белке", layout="wide", page_icon="🃏")

# --- СТИЛИЗАЦИЯ И ИНТЕРФЕЙС (Зеленое сукно) ---
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
        font-size: 14px !important;
    }
    [data-testid="stCheckbox"] label p { color: #ffffff !important; }
    div.stButton > button {
        width: 100% !important;
        background-color: #1e7e34 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: 1px solid #28a745 !important;
        padding: 0.5rem 1rem !important;
    }
    div.stButton > button:hover { background-color: #218838 !important; }
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: bold !important;
        padding: 12px 16px !important;
        color: #a3cfbb !important;
    }
    button[aria-selected="true"] { color: #ffffff !important; border-bottom-color: #28a745 !important; }
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; }
    hr { border-top: 1px solid #1e7e34 !important; }
    </style>
""", unsafe_allow_html=True)

# Инициализация подключения к Google Sheets через Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Читаем данные с листов 'players' и 'games'
        df_p = conn.read(worksheet="players", ttl=5)
        df_g = conn.read(worksheet="games", ttl=5)
        
        players = df_p['Имя'].dropna().tolist() if not df_p.empty and 'Имя' in df_p.columns else []
        games = df_g.to_dict(orient='records') if not df_g.empty else []
        
        # Превращаем строки с игроками обратно в списки для логики пар
        for g in games:
            if isinstance(g.get('win_team'), str):
                g['win_team'] = [x.strip() for x in g['win_team'].split(',')]
            if isinstance(g.get('loss_team'), str):
                g['loss_team'] = [x.strip() for x in g['loss_team'].split(',')]
                
        if not players:
            players = ["Данияр", "Азирхан", "Талгат", "Елдар", "Марат", "Рустем", "Ерлан", "Каиржан", "Аманат", "Мирхат", "Шынгыс"]
            
        return players, games
    except Exception as e:
        # Резервный вариант, если таблица еще совсем пустая
        return ["Данияр", "Азирхан", "Талгат", "Елдар", "Марат", "Рустем", "Ерлан", "Каиржан", "Аманат", "Мирхат", "Шынгыс"], []

# Загрузка актуальных данных в сессию
st.session_state.players, st.session_state.games = load_data()

POINTS_DICT = {
    "Сокыр (24 очка)": 24,
    "Теке (6 очков)": 6,
    "Голый (3 очка)": 3,
    "Обычная игра (0 очков)": 0
}

def calculate_match_points(status, eggs):
    base_points = POINTS_DICT[status]
    return (base_points + 2, 0) if eggs else (base_points, 0)

# --- РАСЧЕТ СТАТИСТИКИ ИЗ ОБЛАКА ---
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
    try:
        win_team = game.get("win_team", [])
        loss_team = game.get("loss_team", [])
        if len(win_team) < 2 or len(loss_team) < 2: continue
        
        win_pair = tuple(sorted(win_team))
        if win_pair not in pairs_stats: pairs_stats[win_pair] = {"Очки": 0, "Игры": 0}
        pairs_stats[win_pair]["Очки"] += int(game["win_points"])
        pairs_stats[win_pair]["Игры"] += 1

        for p in win_team:
            if p in stats:
                stats[p]["Очки"] += int(game["win_points"])
                stats[p]["Игры"] += 1
                if "Сокыр" in str(game["raw_status"]): stats[p]["Выигр. Сокыр"] += 1
                elif "Теке" in str(game["raw_status"]): stats[p]["Выигр. Теке"] += 1
                elif "Голый" in str(game["raw_status"]): stats[p]["Выигр. Голый"] += 1
                if bool(game.get("eggs_happened", False)): stats[p]["Выигр. Яйца"] += 1
                
        for p in loss_team:
            if p in stats: 
                stats[p]["Игры"] += 1
                if "Сокыр" in str(game["raw_status"]): stats[p]["Проигр. Сокыр"] += 1
                elif "Теке" in str(game["raw_status"]): stats[p]["Проигр. Теке"] += 1
                elif "Голый" in str(game["raw_status"]): stats[p]["Проигр. Голый"] += 1
                if bool(game.get("eggs_happened", False)): stats[p]["Проигр. Яйца"] += 1
    except:
        continue

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

# === ЭЛЕМЕНТЫ ИНТЕРФЕЙСА ===
st.title("🃏 Чемпионат по Белке")
if st.button("🔄 Обновить из Облака"):
    st.cache_data.clear()
    st.rerun()

st.markdown("### 🏆 Главная турнирная таблица")
df_main = df_leaderboard.sort_values(by=["Всего очков", "Средний балл"], ascending=[False, False]).reset_index(drop=True)
df_main.index = df_main.index + 1
st.dataframe(df_main, use_container_width=True)

st.markdown("---")

# Вкладки аналитики
tab_history, tab_positive, tab_negative, tab_pairs = st.tabs([
    "📝 История игр", "🚀 Раздали", "📉 Словленные", "👥 Связки"
])

with tab_history:
    if st.session_state.games:
        log_data = []
        for i, g in enumerate(st.session_state.games, 1):
            log_data.append({
                "Матч №": i,
                "Победители": f"{g['win_team'][0]}, {g['win_team'][1]}",
                "Проигравшие": f"{g['loss_team'][0]}, {g['loss_team'][1]}",
                "Статус": g.get("status", g.get("raw_status")),
                "Очки": f"+{g['win_points']}"
            })
        st.dataframe(pd.DataFrame(log_data)[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("В облаке пока нет записанных игр.")

# Регистрация игры (Форма)
col_bottom1, col_bottom2 = st.columns([1, 1])

with col_bottom1:
    st.markdown("### ➕ Регистрация игры")
    match_password = st.text_input("🔑 Пароль:", type="password")
    
    with st.form("match_form", clear_on_submit=True):
        p1 = st.selectbox("Победитель 1", st.session_state.players, index=0)
        p2 = st.selectbox("Победитель 2", st.session_state.players, index=1)
        p3 = st.selectbox("Проигравший 1", st.session_state.players, index=2)
        p4 = st.selectbox("Проигравший 2", st.session_state.players, index=3)
        status = st.selectbox("Что дали?", list(POINTS_DICT.keys()))
        eggs = st.checkbox("Повесили «Яйца» (+2 очка)")
        
        if st.form_submit_button("СОХРАНИТЬ РЕЗУЛЬТАТ"):
            if match_password != "6666":
                st.error("🔒 Неверный пароль!")
            elif len({p1, p2, p3, p4}) < 4:
                st.error("Ошибка: Игроки дублируются!")
            else:
                win_pts, loss_pts = calculate_match_points(status, eggs)
                
                # Подготовка новой строки для добавления в Google Sheets
                new_game = pd.DataFrame([{
                    "win_team": f"{p1}, {p2}",
                    "loss_team": f"{p3}, {p4}",
                    "win_points": win_pts,
                    "loss_points": loss_pts,
                    "raw_status": status,
                    "eggs_happened": str(eggs).upper(),
                    "status": f"{status} {'+ Яйца' if eggs else ''}",
                    "timestamp": time.time()
                }])
                
                # Дописываем строку в таблицу 'games'
                df_existing_games = conn.read(worksheet="games", ttl=0)
                df_updated_games = pd.concat([df_existing_games, new_game], ignore_index=True)
                conn.update(worksheet="games", data=df_updated_games)
                
                st.success("Результат успешно сохранен в Google Таблицу!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

with col_bottom2:
    st.markdown("### ⚙️ Управление составом")
    with st.expander("Добавить нового игрока в облако"):
        new_player = st.text_input("Имя нового игрока:")
        if st.button("Добавить"):
            if match_password != "6666":
                st.error("Пароль!")
            elif new_player.strip():
                df_existing_p = conn.read(worksheet="players", ttl=0)
                new_p_df = pd.DataFrame([{"Имя": new_player.strip()}])
                df_updated_p = pd.concat([df_existing_p, new_p_df], ignore_index=True)
                conn.update(worksheet="players", data=df_updated_p)
                st.success("Игрок добавлен в базу!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
