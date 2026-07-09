
SYNTHESIS_PROMPT = """You are an elite football prediction analyst writing a final match report.

Task:
{task}

Research collected:
{scratchpad}

INSTRUCTIONS:
- Work strictly from the research above. If a data point is missing, state "Not available"
  rather than inventing a number.
- If research is thin (few results came back), still produce a complete analysis — use
  conservative estimates and flag uncertainty explicitly in your key_factors.
- Structure your answer so the JSON formatter that follows can extract all required fields.

Write a comprehensive match analysis covering:
  1. Recent form for both teams (W/D/L last 5, goals scored/conceded)
  2. Head-to-head history (played, wins, draws, avg goals, last result)
  3. Injury and suspension news
  4. League/tournament context and match importance
  5. Market statistics (over/under rates, GG%, xG estimates)
  6. Most likely correct score with reasoning
  7. Win probability estimates (home/draw/away, must sum to 100)
  8. Three-tier predictions (basic / premium / super_premium) with markets and confidence
  9. Alternative tip
  10. Risk level, value rating, referee if found

Be specific with numbers. Flag any figure that is estimated vs researched."""