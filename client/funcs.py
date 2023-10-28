
def generate_time(time):
    timeSeconds = time
    day = timeSeconds // (24 * 3600)
    timeSeconds = timeSeconds % (24 * 3600)
    hour = timeSeconds // 3600
    timeSeconds %= 3600
    minutes = timeSeconds // 60
    timeSeconds %= 60
    seconds = timeSeconds

    day = f" {round(day)}d" if day != 0 else ""
    hour = f" {round(hour)}h" if hour != 0 else ""
    minutes = f" {round(minutes)}m" if minutes != 0 else ""

    if day == "" and hour == "" and minutes == "":
        return f"{round(seconds)}s"
    
    return f"{day}{hour}{minutes}".lstrip()

def top_rankings_to_text(rankings : dict, object_name : str, notable_only = True) -> str:
    notable_statistics = ""
    for (leaderboard), (value, ranking, notable) in rankings.items():
        if notable: notable_statistics += f"\n- {object_name} is **#{ranking}** on the **{leaderboard.replace('_', ' ')}** ranking"
    if not notable_only or notable_statistics == "": notable_statistics = "None"

    return notable_statistics