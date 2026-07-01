import streamlit as st
import pandas as pd
import json
import os
import time

st.set_page_config(page_title="Чемпионат по Белке", layout="wide", page_icon="🃏")

PLAYERS_FILE = "belka_players.json"
GAMES_FILE = "belka_games.json"

# --- БЕЗОПАСНЫЕ ФУНКЦИИ С ЧТЕНИЕМ И ЗАПИСЬЮ (ЗАЩИТА ОТ ОДНОВРЕМЕННОГО ДУБЛИРОВАНИЯ) ---
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

# Всегда актуализируем данные при действиях, чтобы видеть то, что ввели с других ПК
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

st.title("🃏 Чемпионат по карточной игре «Белка»")
st.subheader("Сетевая система учета результатов")

# Кнопка ручного обновления, если кто-то другой забил игру, а у вас открыта вкладка
if st.button("🔄 Обновить таблицу (Загрузить новые игры с сервера)"):
    load_data()
    st.rerun()

col_form, col_table = st.columns([1, 1.5])

with col_form:
    st.markdown("### ➕ Регистрация сыгранной игры")
    with st.form("match_form", clear_on_submit=False):
        st.markdown("**КОМАНДА 1 (Победители)**")
        p1 = st.selectbox("Победитель 1", st.session_state.players, index=0 if len(st.session_state.players) > 0 else None)
        p2 = st.selectbox("Победитель 2", st.session_state.players, index=1 if len(st.session_state.players) > 1 else None)
        
        st.markdown("**КОМАНДА 2 (Проигравшие)**")
        p3 = st.selectbox("Проигравший 1", st.session_state.players, index=2 if len(st.session_state.players) > 2 else None)
        p4 = st.selectbox("Проигравший 2", st.session_state.players, index=3 if len(st.session_state.players) > 3 else None)
        
        st.markdown("**РЕЗУЛЬТАТ ИГРЫ**")
        status = st.selectbox("Что дали победители?", list(POINTS_DICT.keys()))
        eggs = st.checkbox("Повесили «Яйца» (+2 очка победителям)")
        
        submit = st.form_submit_button("СОХРАНИТЬ РЕЗУЛЬТАТ ИГРЫ")
        
        if submit:
            if not (p1 and p2 and p3 and p4):
                st.error("Ошибка: Недостаточно игроков!")
            else:
                selected_players = [p1, p2, p3, p4]
                if len(set(selected_players)) < 4:
                    st.error("Ошибка: Один и тот же игрок не может быть выбран дважды!")
                else:
                    load_data() # Подгружаем свежее перед записью
                    win_pts, loss_pts = calculate_match_points(status, eggs)
                    match_data = {
                        "win_team": [p1, p2],
                        "loss_team": [p3, p4],
                        "win_points": win_pts,
                        "loss_points": loss_pts,
                        "raw_status": status,
                        "status": f"{status} {'+ Яйца' if eggs else ''}",
                        "timestamp": time.time()
                    }
                    st.session_state.games.append(match_data)
                    save_games()
                    st.success(f"Сохранено! Победителям начислено: +{win_pts} очков.")
                    st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Управление составом игроков")
    
    with st.expander("➕ Добавить нового игрока"):
        new_player = st.text_input("Имя нового участника:")
        if st.button("Зарегистрировать игрока"):
            load_data()
            if new_player.strip() == "": st.error("Имя пустое!")
            elif new_player in st.session_state.players: st.error("Уже есть!")
            else:
                st.session_state.players.append(new_player.strip())
                save_players()
                st.success(f"Добавлен {new_player}!")
                st.rerun()

    with st.expander("❌ Удалить игрока из списка"):
        player_to_remove = st.selectbox("Выберите кого удалить:", st.session_state.players, key="remove_select")
        if st.button("Удалить игрока навсегда"):
            load_data()
            st.session_state.players.remove(player_to_remove)
            save_players()
            st.warning(f"Игрок {player_to_remove} удален.")
            st.rerun()

stats = {player: {"Очки": 0, "Игры": 0, "Средний балл": 0.0, "Сокыр": 0, "Теке": 0, "Голый": 0} for player in st.session_state.players}
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
            if "Сокыр" in game["raw_status"]: stats[p]["Сокыр"] += 1
            elif "Теке" in game["raw_status"]: stats[p]["Теке"] += 1
            elif "Голый" in game["raw_status"]: stats[p]["Голый"] += 1
    for p in game["loss_team"]:
        if p in stats: stats[p]["Игры"] += 1

for player in stats:
    if stats[player]["Игры"] > 0:
        stats[player]["Средний балл"] = round(stats[player]["Очки"] / stats[player]["Игры"], 2)

with col_table:
    st.markdown("### 🏆 Главная турнирная таблица")
    df_leaderboard = pd.DataFrame.from_dict(stats, orient='index').reset_index()
    df_leaderboard.columns = ["Игрок", "Всего очков", "Сыграно игр", "Средний балл", "Сокыр", "Теке", "Голый"]
    
    df_main = df_leaderboard[["Игрок", "Всего очков", "Сыграно игр", "Средний балл"]].sort_values(by=["Всего очков", "Средний балл"], ascending=[False, False]).reset_index(drop=True)
    df_main.index = df_main.index + 1
    st.dataframe(df_main, use_container_width=True)
    
    st.markdown("---")
    with st.expander("🚨 Сброс результатов турнира (Требуется пароль)"):
        input_password = st.text_input("Введите секретный код для полного удаления данных:", type="password")
        if st.button("Подтвердить полное уничтожение данных таблицы"):
            if input_password == "5559":
                st.session_state.games = []
                save_games()
                st.success("Все данные удалены!")
                st.rerun()
            else:
                st.error("Неверный пароль!")

st.markdown("---")
st.markdown("### 📊 Дополнительная аналитика чемпионата")
tab1, tab2, tab3, tab4 = st.tabs(["🔥 Рейтинг по Сокырам", "🐐 Рейтинг по Теке", "🪵 Рейтинг по Голым", "👥 Лучшая результативность пар"])

with tab1:
    st.dataframe(df_leaderboard[["Игрок", "Сокыр"]].sort_values(by="Сокыр", ascending=False).reset_index(drop=True), use_container_width=True)
with tab2:
    st.dataframe(df_leaderboard[["Игрок", "Теке"]].sort_values(by="Теке", ascending=False).reset_index(drop=True), use_container_width=True)
with tab3:
    st.dataframe(df_leaderboard[["Игрок", "Голый"]].sort_values(by="Голый", ascending=False).reset_index(drop=True), use_container_width=True)
with tab4:
    if pairs_stats:
        pairs_list = [{"Связка / Пара игроков": f"{k[0]} 🤝 {k[1]}", "Набранные очки пары": v["Очки"], "Совместных игр": v["Игры"], "Эффективность пары (средняя)": round(v["Очки"] / v["Игры"], 2)} for k, v in pairs_stats.items()]
        st.dataframe(pd.DataFrame(pairs_list).sort_values(by=["Набранные очки пары", "Эффективность пары (средняя)"], ascending=[False, False]).reset_index(drop=True), use_container_width=True)
    else:
        st.info("Матчей пока нет.")

st.markdown("---")
st.markdown("### 📝 История всех матчей")
if st.session_state.games:
    log_data = []
    # Сортируем историю: новые игры вверху
    sorted_games = sorted(st.session_state.games, key=lambda x: x.get('timestamp', 0), reverse=True)
    for idx, g in enumerate(sorted_games, 1):
        log_data.append({"№": idx, "Победители": f"{g['win_team'][0]}, {g['win_team'][1]}", "Проигравшие": f"{g['loss_team'][0]}, {g['loss_team'][1]}", "Что произошло": g["status"], "Очки выигравших": f"+{g['win_points']}"})
    st.table(log_data)