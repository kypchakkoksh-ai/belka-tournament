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
    df_glaza = df_leaderboard[["Игрок", "глаза_выигр", "глаза_проигр", "глаза_разница"]].copy()
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
