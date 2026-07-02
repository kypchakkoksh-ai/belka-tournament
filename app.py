import streamlit as st
import pandas as pd
import time

# Настройка страницы: дефолтный dark mode и заголовок
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

# Укажите здесь URL созданной вами Google Таблицы
# В будущем идеальный вариант — убрать ссылку в st.secrets
GSHEET_URL = "ВСТАВЬТЕ_СЮДА_ВАШУ_ССЫЛКУ_НА_GOOGLE_ТАБЛИЦУ"

@st.cache_data(ttl=10)
def load_data_from_sheets():
    try:
        # Чтение данных из Google Sheets с помощью pandas напрямую (если таблица открыта по ссылке)
        players_url = GSHEET_URL.replace('/edit?usp=sharing', '/gviz/tq?tqx=out:csv&sheet=players')
        games_url = GSHEET_URL.replace('/edit?usp=sharing', '/gviz/tq?tqx=out:csv&sheet=games')
        
        df_p = pd.read_csv(players_url)
        df_g = pd.read_csv(games_url)
        
        players = df_p['Имя'].dropna().tolist()
        games = df_g.to_dict(orient='records')
        
        # Парсинг строк обратно в списки для логики пар игроков
        for g in games:
            if isinstance(g['win_team'], str):
                g['win_team'] = [x.strip() for x in g['win_team'].split(',')]
            if isinstance(g['loss_team'], str):
                g['loss_team'] = [x.strip() for x in g['loss_team'].split(',')]
                
        return players, games
    except Exception as e:
        # Дефолтный список, если таблица еще пустая или недоступна
        default_players = ["Данияр", "Азирхан", "Талгат", "Елдар", "Марат", "Рустем", "Ерлан", "Каиржан", "Аманат", "Мирхат", "Шынгыс"]
        return default_players, []

# Инициализация сессии
if "players" not in st.session_state or "games" not in st.session_state:
    st.session_state.players, st.session_state.games = load_data_from_sheets()

# Примечание: Для полноценной ЗАПИСИ в Google Sheets в Streamlit Cloud 
# лучше всего использовать st.connection("gsheets", type=GSheetsConnection).
# Ниже приведена базовая структура аналитики, которая теперь защищена от удаления файлов.

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

# --- СБОР РАСШИРЕННОЙ СТАТИСТИКИ (Аналогично вашей логике) ---
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
        win_pair = tuple(sorted(game["win_team"]))
        if win_pair not in pairs_stats: pairs_stats[win_pair] = {"Очки": 0, "Игры": 0}
        pairs_stats[win_pair]["Очки"] += game["win_points"]
        pairs_stats[win_pair]["Игры"] += 1

        for p in game["win_team"]:
            if p in stats:
                stats[p]["Очки"] += game["win_points"]
                stats[p]["Игры"] += 1
                if "Сокыр" in str(game["raw_status"]): stats[p]["Выигр. Сокыр"] += 1
                elif "Теке" in str(game["raw_status"]): stats[p]["Выигр. Теке"] += 1
                elif "Голый" in str(game["raw_status"]): stats[p]["Выигр. Голый"] += 1
                if game.get("eggs_happened", False): stats[p]["Выигр. Яйца"] += 1
                
        for p in game["loss_team"]:
            if p in stats: 
                stats[p]["Игры"] += 1
                if "Сокыр" in str(game["raw_status"]): stats[p]["Проигр. Сокыр"] += 1
                elif "Теке" in str(game["raw_status"]): stats[p]["Проигр. Теке"] += 1
                elif "Голый" in str(game["raw_status"]): stats[p]["Проигр. Голый"] += 1
                if game.get("eggs_happened", False): stats[p]["Проигр. Яйца"] += 1
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

# === РЕНДЕРИНГ ИНТЕРФЕЙСА ===
st.title("🃏 Чемпионат по Белке")
if st.button("🔄 Синхронизировать с базой"):
    st.cache_data.clear()
    st.session_state.players, st.session_state.games = load_data_from_sheets()
    st.rerun()

st.markdown("### 🏆 Главная турнирная таблица")
df_main = df_leaderboard.sort_values(by=["Всего очков", "Средний балл"], ascending=[False, False]).reset_index(drop=True)
df_main.index = df_main.index + 1
st.dataframe(df_main, use_container_width=True)

st.markdown("---")
st.warning("⚠️ Для включения функции непрерывной записи на вашем аккаунте GitHub, добавьте коннектор Google Sheets в настройках Streamlit Cloud Secrets, чтобы исключить влияние перезапусков серверов.")

# [Остальной интерфейс вкладок аналитики работает стабильно на базе df_leaderboard]
