@st.cache_data
def generate_pure_round_robin_45_teams():
    # Создаем жестко фиксированный список 45 команд
    teams = [f"Команда {i:02d}" for i in range(1, 46)]
    schedule = []
    
    # Всего 45 туров
    for tour in range(1, 46):
        # В каждом туре отдыхает элемент, смещающийся с конца
        bypass_idx = (45 - tour) % 45
        bypass_team = teams[bypass_idx]
        
        # Собираем список активных команд для текущего тура
        active_teams = teams[bypass_idx + 1:] + teams[:bypass_idx]
        
        tour_matches = []
        # Разбиваем 44 активные команды на 22 пары зеркальным сдвигом (первый с последним)
        for i in range(22):
            home = active_teams[i]
            away = active_teams[43 - i]
            tour_matches.append((home, away))
            
        # Записываем в общую структуру
        for match_idx, (t1, t2) in enumerate(tour_matches, 1):
            schedule.append({
                "stage": (tour - 1) // 5 + 1,  # Автоматическое деление на 9 этапов по 5 туров
                "tour": tour,
                "match_num": f"Матч {match_idx:02d}",
                "team1": t1,
                "team2": t2,
                "bypass": bypass_team
            })
            
    return schedule
