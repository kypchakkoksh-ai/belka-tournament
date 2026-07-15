@st.cache_data(ttl=1)  # Уменьшили TTL до 1 секунды для надежности
def load_data_from_sheets():
    if gc is None:
        return DEFAULT_PLAYERS.copy(), []
    try:
        sh = gc.open_by_url(st.secrets["spreadsheet_url"])
        
        # Загрузка игроков
        try:
            worksheet_p = sh.worksheet("players")
            players = [x for x in worksheet_p.col_values(1) if x and x != 'Имя']
            if not players:
                players = DEFAULT_PLAYERS.copy()
        except:
            players = DEFAULT_PLAYERS.copy()
            
        # Загрузка матчей
        try:
            worksheet_g = sh.worksheet("games")
            all_records = worksheet_g.get_all_records()
            df_g = pd.DataFrame(all_records)
            games = df_g.to_dict(orient='records') if not df_g.empty else []
        except Exception as e:
            games = []
            
        for g in games:
            if isinstance(g.get('win_team'), str):
                g['win_team'] = [x.strip() for x in g['win_team'].split(',')]
            if isinstance(g.get('loss_team'), str):
                g['loss_team'] = [x.strip() for x in g['loss_team'].split(',')]
        return players, games
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return DEFAULT_PLAYERS.copy(), []
