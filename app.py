import streamlit as st
import pandas as pd
import json
import os
import time

st.set_page_config(page_title="Чемпионат по Белке", layout="wide", page_icon="🃏")

PLAYERS_FILE = "belka_players.json"
GAMES_FILE = "belka_games.json"

# --- БЕЗОПАСНАЯ СИНХРОНИЗАЦИЯ С ДИСКОМ ---
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

st.title("🃏 Чемпионат по карточной игре «Белка»")
st.subheader("Сетевая система учета результатов")

if st.button("🔄 Обновить таблицу (Загрузить новые данные)"):
    load_data()
    st.rerun()

col_form, col_table = st.columns([1, 1.4])

# --- ЛЕВАЯ КОЛОНКА: ВВОД И УПРАВЛЕНИЕ ---
with col_form:
    st.markdown("### ➕ Регистрация сыгранной игры")
    
    match_password = st.text_input("🔑 Пароль администратора (Ввод / Правка):", type="password", help="Введите 6666, чтобы разблокировать управление матчами")
    
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
            if match_password != "6666":
                st.error("🔒 Отказано в доступе! Неверный пароль администратора.")
            elif not (p1 and p2 and p3 and p4):
                st.error("Ошибка: Недостаточно игроков!")
            else:
                selected_players = [p1, p2, p3, p4]
                if len(set(selected_players)) < 4:
                    st.error("Ошибка: Один и тот же игрок не может быть выбран дважды!")
                else:
                    load_data()
                    win_pts, loss_pts = calculate_match_points(status, eggs)
                    match_data = {
                        "win_team": [p1, p2],
                        "loss_team": [p3, p4],
                        "win_points": win_pts,
                        "loss_points": loss_pts,
                        "raw_status": status,
                        "eggs_happened": eggs,
                        "status": f"{status} {'+ Яйца' if eggs else ''}",
                        "timestamp": time.time()
                    }
                    st.session_state.games.append(match_data)
                    save_games()
                    st.success(f"Успешно сохранено! Победителям начислено: +{win_pts} очков.")
                    st.rerun()

    # --- КОРРЕКТИРОВКА И УДАЛЕНИЕ МАТЧЕЙ ---
    st.markdown("---")
    st.markdown("### ✏️ Корректировка прошедших матчей")
    
    with st.expander("Изменить или удалить конкретную игру"):
        if not st.session_state.games:
            st.info("История матчей пуста.")
        else:
            match_indices = list(range(1, len(st.session_state.games) + 1))
            selected_match_num = st.selectbox("Выберите номер матча из истории (№):", match_indices)
            
            target_idx = selected_match_num - 1
            current_match = st.session_state.games[target_idx]
            
            st.markdown(f"**Текущие данные матча №{selected_match_num}:** \n"
                        f"Победили: *{current_match['win_team'][0]}, {current_match['win_team'][1]}* \n"
                        f"Проиграли: *{current_match['loss_team'][0]}, {current_match['loss_team'][1]}* \n"
                        f"Исход: *{current_match['status']}*")
            
            st.markdown("---")
            st.markdown("**Новые параметры для этого матча:**")
            
            try: edit_p1_idx = st.session_state.players.index(current_match['win_team'][0])
            except: edit_p1_idx = 0
            try: edit_p2_idx = st.session_state.players.index(current_match['win_team'][1])
            except: edit_p2_idx = 1
            try: edit_p3_idx = st.session_state.players.index(current_match['loss_team'][0])
            except: edit_p3_idx = 2
            try: edit_p4_idx = st.session_state.players.index(current_match['loss_team'][1])
            except: edit_p4_idx = 3
            try: edit_status_idx = list(POINTS_DICT.keys()).index(current_match['raw_status'])
            except: edit_status_idx = 0

            edit_p1 = st.selectbox("Новый Победитель 1", st.session_state.players, index=edit_p1_idx, key="e_p1")
            edit_p2 = st.selectbox("Новый Победитель 2", st.session_state.players, index=edit_p2_idx, key="e_p2")
            edit_p3 = st.selectbox("Новый Проигравший 1", st.session_state.players, index=edit_p3_idx, key="e_p3")
            edit_p4 = st.selectbox("Новый Проигравший 2", st.session_state.players, index=edit_p4_idx, key="e_p4")
            edit_status = st.selectbox("Новый исход", list(POINTS_DICT.keys()), index=edit_status_idx, key="e_stat")
            edit_eggs = st.checkbox("Повесили «Яйца»", value=current_match.get("eggs_happened", False), key="e_eggs")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("💾 Сохранить изменения", key="save_edit_btn"):
                    if match_password != "6666":
                        st.error("🔒 Неверный пароль!")
                    elif len({edit_p1, edit_p2, edit_p3, edit_p4}) < 4:
                        st.error("Ошибка: Игроки дублируются!")
                    else:
                        load_data()
                        win_pts, loss_pts = calculate_match_points(edit_status, edit_eggs)
                        st.session_state.games[target_idx] = {
                            "win_team": [edit_p1, edit_p2],
                            "loss_team": [edit_p3, edit_p4],
                            "win_points": win_pts,
                            "loss_points": loss_pts,
                            "raw_status": edit_status,
                            "eggs_happened": edit_eggs,
                            "status": f"{edit_status} {'+ Яйца' if edit_eggs else ''}",
                            "timestamp": current_match.get('timestamp', time.time())
                        }
                        save_games()
                        st.success(f"Матч №{selected_match_num} успешно изменен!")
                        st.rerun()
                        
            with col_btn2:
                if st.button("🗑️ Полностью удалить этот матч", key="delete_match_btn"):
                    if match_password != "6666":
                        st.error("🔒 Неверный пароль!")
                    else:
                        load_data()
                        st.session_state.games.pop(target_idx)
                        save_games()
                        st.warning(f"Матч №{selected_match_num} полностью удален из истории!")
                        st.rerun()

    # --- УПРАВЛЕНИЕ СПИСКОМ ИГРОКОВ ---
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

# --- ПРАВАЯ КОЛОНКА: ГЛАВНЫЙ ЭКРАН ---
with col_table:
    st.markdown("### 🏆 Главная турнирная таблица чемпионата")
    
    df_main = df_leaderboard.sort_values(by=["Всего очков", "Средний балл"], ascending=[False, False]).reset_index(drop=True)
    df_main.index = df_main.index + 1
    st.dataframe(df_main, use_container_width=True)
    
    st.markdown("---")
    with st.expander("🚨 Сброс результатов турнира (Требуется пароль организатора)"):
        input_password = st.text_input("Введите секретный код для удаления всех игр турнира:", type="password", key="clear_pass")
        if st.button("Подтвердить полное уничтожение данных таблицы"):
            if input_password == "5559":
                st.session_state.games = []
                save_games()
                st.success("Все матчи успешно стёрты!")
                st.rerun()
            else:
                st.error("Неверный пароль доступа.")

# --- НИЖНЯЯ ПАНЕЛЬ: АНАЛИТИКА ---
st.markdown("---")
st.markdown("### 📊 Дополнительная аналитика чемпионата")

# Разделяем на верхние глобальные вкладки
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "🚀 Положительный рейтинг (Кто раздал)", 
    "📉 Отрицательный рейтинг (Кто поймал)", 
    "👥 Результативность пар", 
    "📝 История всех матчей"
])

# 1. ПОЛОЖИТЕЛЬНЫЙ РЕЙТИНГ
with main_tab1:
    st.markdown("#### 🏆 Лидеры по раздаче особых статусов (Сортировка от большего к меньшему)")
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🔥 Выданные Сокыры", "🐐 Выданные Теке", "🪵 Выданные Голые", "🥚 Повешенные Яйца"])
    
    with sub_tab1:
        st.dataframe(df_leaderboard[["Игрок", "Выигр. Сокыр"]].sort_values(by="Выигр. Сокыр", ascending=False).reset_index(drop=True), use_container_width=True)
    with sub_tab2:
        st.dataframe(df_leaderboard[["Игрок", "Выигр. Теке"]].sort_values(by="Выигр. Теке", ascending=False).reset_index(drop=True), use_container_width=True)
    with sub_tab3:
        st.dataframe(df_leaderboard[["Игрок", "Выигр. Голый"]].sort_values(by="Выигр. Голый", ascending=False).reset_index(drop=True), use_container_width=True)
    with sub_tab4:
        st.dataframe(df_leaderboard[["Игрок", "Повесили Яйца"]].sort_values(by="Повесили Яйца", ascending=False).reset_index(drop=True), use_container_width=True)

# 2. ОТРИЦАТЕЛЬНЫЙ РЕЙТИНГ
with main_tab2:
    st.markdown("#### 🚨 «Анти-лидеры» турнира — те, кто чаще всего ловил раздачи (Сортировка от худшего к лучшему)")
    neg_tab1, neg_tab2, neg_tab3, neg_tab4 = st.tabs(["👁️ Пойманные Сокыры", "🐐 Полученные Теке", "🪵 Полученные Голые", "🥚 Словленные Яйца"])
    
    with neg_tab1:
        st.dataframe(df_leaderboard[["Игрок", "Проигр. Сокыр"]].sort_values(by="Проигр. Сокыр", ascending=False).reset_index(drop=True), use_container_width=True)
    with neg_tab2:
        st.dataframe(df_leaderboard[["Игрок", "Проигр. Теке"]].sort_values(by="Проигр. Теке", ascending=False).reset_index(drop=True), use_container_width=True)
    with neg_tab3:
        st.dataframe(df_leaderboard[["Игрок", "Проигр. Голый"]].sort_values(by="Проигр. Голый", ascending=False).reset_index(drop=True), use_container_width=True)
    with neg_tab4:
        st.dataframe(df_leaderboard[["Игрок", "Получили Яйца"]].sort_values(by="Получили Яйца", ascending=False).reset_index(drop=True), use_container_width=True)

# 3. РЕЙТИНГ ПАР
with main_tab3:
    st.markdown("#### 👥 Совместная результативность связок")
    if pairs_stats:
        pairs_list = [{"Связка / Пара игроков": f"{k[0]} 🤝 {k[1]}", "Набранные очки пары": v["Очки"], "Совместных игр": v["Игры"], "Эффективность пары (средняя)": round(v["Очки"] / v["Игры"], 2)} for k, v in pairs_stats.items()]
        df_pairs_final = pd.DataFrame(pairs_list).sort_values(by=["Набранные очки пары", "Эффективность пары (средняя)"], ascending=[False, False]).reset_index(drop=True)
        df_pairs_final.index = df_pairs_final.index + 1
        st.dataframe(df_pairs_final, use_container_width=True)
    else:
        st.info("Матчей пока нет.")

# 4. ИСТОРИЯ
with main_tab4:
    st.markdown("#### 📝 История всех сыгранных матчей")
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
                "Очки выигравших": f"+{g['win_points']}"
            })
        st.table(log_data)
    else:
        st.info("Игр еще не было.")
