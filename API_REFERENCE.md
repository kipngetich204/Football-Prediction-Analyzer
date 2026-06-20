# Football Prediction API Reference

## Quick Reference

### Main API Functions

#### 1. `predict_match(match_data: dict) -> dict`
Generate a single prediction for a football match.

**Usage:**
```python
from app.football_main import predict_match

match = {
    "homeTeam": "Ecuador",
    "awayTeam": "Curaçao",
    "date": "2026-06-20",
    "league": "FIFA World Cup",
    "id": "537354",
    "livescoreId": "537354"
}

result = predict_match(match)
```

**Returns:** Dictionary with 25+ prediction fields

**Input Requirements:**
- `homeTeam` (required)
- `awayTeam` (required)  
- `date` (required)
- `league` (required)
- `id` (required)
- `livescoreId` (required)

**Optional Fields:**
- `time`, `score`, `matchStatus`, `markets`, `type`, `status`

---

#### 2. `batch_predict(matches_file: str) -> list[dict]`
Process multiple matches from a JSON file.

**Usage:**
```python
from app.football_main import batch_predict
import json

predictions = batch_predict('matches.json')

# Save to file
with open('results.json', 'w') as f:
    json.dump(predictions, f, indent=2)
```

**Input Format:**
```json
[
  {
    "homeTeam": "Team A",
    "awayTeam": "Team B",
    ...
  },
  {
    "homeTeam": "Team C",
    "awayTeam": "Team D",
    ...
  }
]
```

**Returns:** List of prediction dictionaries

---

### Agent API (Lower Level)

#### `FootballPredictionAgent`

**Initialization:**
```python
from agent.football_agent import FootballPredictionAgent

agent = FootballPredictionAgent(
    model="qwen2.5:3b",
    ollama_base_url="http://localhost:11434"
)
```

**Methods:**

##### `analyze_match(match_data: dict) -> FootballPredictionOutput`
Main analysis method.

```python
prediction = agent.analyze_match(match_data)
print(prediction.prediction)
print(prediction.confidence_score)
```

##### `_get_team_stats(team: str, league: str) -> dict`
Get team statistics.

##### `_get_head_to_head(home_team: str, away_team: str) -> dict`
Get H2H history.

##### `_get_form(team: str) -> dict`
Get team form analysis.

##### `_get_injuries(team: str) -> dict`
Get injury information.

---

### Tools API (For Advanced Users)

#### Available Tools

```python
from tools.football_tools import (
    TeamStatsTool,
    HeadToHeadTool, 
    FormAnalysisTool,
    InjuryDataTool
)

# Each tool has:
# - name: str
# - description: str
# - args_schema: Pydantic model
# - run(args) -> str
# - safe_run(args) -> tuple[str, bool]
```

---

## Output Schema

### Main Output Object

```python
{
    # Match Identification (6 fields)
    "id": str,
    "livescoreId": str,
    "date": str,  # YYYY-MM-DD
    "league": str,
    "homeTeam": str,
    "awayTeam": str,
    
    # Match Details (5 fields)
    "time": str,  # HH:MM
    "score": str,
    "matchStatus": str,  # "Not Started" | "Live" | "Finished"
    "markets": str,
    
    # Predictions (4 fields)
    "prediction": str,
    "reason": str,
    "type": str,  # "basic" | "premium" | "super-premium"
    "status": str,  # "pending" | "won" | "lost"
    
    # Advanced Analysis (7 fields)
    "expected_score": str,
    "confidence_score": int,  # 0-100
    "risk_level": str,  # "Low" | "Medium" | "High"
    "value_rating": int,  # 1-5
    "tip_of_the_day": bool,
    "match_importance": str,  # "Low" | "Medium" | "High" | "Critical"
    "league_round": str | None,
    "referee": str | None,
    
    # Probabilities (1 field with nested data)
    "win_probabilities": {
        "home": int,    # 0-100
        "draw": int,    # 0-100
        "away": int     # 0-100
    },
    
    # Expected Goals (1 field with nested data)
    "expected_goals": {
        "home": float,  # 0.3-4.0
        "away": float   # 0.3-4.0
    },
    
    # Form (1 field with nested data)
    "form": {
        "home": str,    # e.g., "WWWDL"
        "away": str     # e.g., "LWWDD"
    },
    
    # Head-to-Head (1 field with nested data)
    "h2h_summary": {
        "played": int,
        "home_wins": int,
        "draws": int,
        "away_wins": int,
        "avg_goals": float,
        "last_meeting": str | None
    },
    
    # Key Factors (1 field with array)
    "key_factors": [str, str, str],  # Up to 10 factors
    
    # Injury Alerts (1 field with nested data)
    "injury_alert": {
        "active": bool,
        "home_team": str | None,
        "away_team": str | None
    },
    
    # Prediction Tiers (3 fields with nested data)
    "basic_prediction": {
        "market": str,
        "prediction": str,
        "reason": str,
        "confidence": int  # 0-100
    },
    
    "premium_prediction": {
        "market": str,
        "prediction": str,
        "reason": str,
        "confidence": int  # 0-100
    },
    
    "super_premium_prediction": {
        "market": str,
        "prediction": str,
        "reason": str,
        "confidence": int  # 0-100
    } | None,
    
    "alternative_tip": {
        "market": str,
        "prediction": str,
        "reason": str,
        "confidence": int  # 0-100
    }
}
```

**Total Fields: 25+**

---

## Data Models

### Available Pydantic Models

```python
from agent.football_models import (
    FootballPredictionOutput,
    WinProbabilities,
    ExpectedGoals,
    FormData,
    H2HSummary,
    InjuryAlert,
    BasicPrediction
)
```

### Usage Example

```python
from agent.football_models import FootballPredictionOutput

# Validate data
prediction = FootballPredictionOutput(**prediction_dict)

# Access fields
print(prediction.homeTeam)
print(prediction.win_probabilities.home)
print(prediction.expected_goals.home)
```

---

## Constants & Enums

### Risk Levels
- `"Low"` - High confidence (>60%)
- `"Medium"` - Moderate confidence (45-60%)
- `"High"` - Low confidence (<45%)

### Match Status
- `"Not Started"` - Upcoming match
- `"Live"` - Currently in progress
- `"Finished"` - Completed

### Prediction Types
- `"basic"` - Simple prediction
- `"premium"` - Enhanced analysis
- `"super-premium"` - Advanced tier

### Prediction Status
- `"pending"` - Awaiting result
- `"won"` - Prediction correct
- `"lost"` - Prediction incorrect

### Markets
- `"Over 2.5 Goals"` - Total goals over 2.5
- `"GG"` - Both teams to score
- `"1X2"` - Match result (Home/Draw/Away)
- `"BTTS"` - Both teams to score
- `"Handicap"` - Goal handicap betting

### Match Importance
- `"Low"` - Regular match
- `"Medium"` - Important match
- `"High"` - Very important
- `"Critical"` - Championship/Final

---

## Example Workflows

### Workflow 1: Single Prediction with Full Analysis

```python
from app.football_main import predict_match
import json

match = {
    "homeTeam": "Ecuador",
    "awayTeam": "Curaçao",
    "date": "2026-06-20",
    "league": "FIFA World Cup",
    "id": "537354",
    "livescoreId": "537354",
    "markets": "Over 2.5 Goals",
    "type": "premium"
}

result = predict_match(match)

# Extract key information
print(f"Prediction: {result['prediction']}")
print(f"Confidence: {result['confidence_score']}%")
print(f"Risk: {result['risk_level']}")
print(f"Home Win Chance: {result['win_probabilities']['home']}%")
print(f"Expected Score: {result['expected_score']}")

# Save detailed prediction
with open('prediction.json', 'w') as f:
    json.dump(result, f, indent=2)
```

### Workflow 2: Compare Multiple Matches

```python
from app.football_main import batch_predict
import json

# Create batch file
matches = [
    {"homeTeam": "Brazil", "awayTeam": "France", ...},
    {"homeTeam": "Germany", "awayTeam": "Spain", ...},
    {"homeTeam": "Argentina", "awayTeam": "Italy", ...}
]

with open('matches.json', 'w') as f:
    json.dump(matches, f, indent=2)

# Run batch prediction
predictions = batch_predict('matches.json')

# Analyze results
for pred in predictions:
    print(f"{pred['homeTeam']} vs {pred['awayTeam']}: "
          f"Confidence {pred['confidence_score']}%")
```

### Workflow 3: Filter by Risk Level

```python
from app.football_main import batch_predict

predictions = batch_predict('matches.json')

# Get low-risk predictions only
low_risk = [p for p in predictions if p['risk_level'] == 'Low']

print(f"Low-risk predictions: {len(low_risk)}")
for pred in low_risk:
    print(f"  {pred['homeTeam']} vs {pred['awayTeam']}")
```

---

## Error Handling

### Common Errors

**Missing Required Fields:**
```python
try:
    result = predict_match({"homeTeam": "Brazil"})
except Exception as e:
    print(f"Error: {e}")  # ValidationError: awayTeam required
```

**Invalid Data Types:**
```python
try:
    result = predict_match({
        "homeTeam": 123,  # Should be str
        ...
    })
except Exception as e:
    print(f"Error: {e}")  # ValidationError: not a valid string
```

**API Connection Issues:**
```python
try:
    agent = FootballPredictionAgent()
    # Ensure Ollama is running on http://localhost:11434
except Exception as e:
    print(f"Connection error: {e}")
```

---

## Performance Notes

- **Single Prediction**: ~1-2 seconds
- **Batch (10 matches)**: ~10-20 seconds
- **Memory Usage**: ~100MB base + ~10MB per prediction
- **Mock Data**: Uses in-memory database (instant access)
- **Real Data**: Will depend on API response time

---

## Future API Additions

Planned for future versions:
- `get_team_history()` - Historical statistics
- `calculate_odds()` - Betting odds integration
- `track_prediction()` - Prediction accuracy tracking
- `get_trending_predictions()` - Popular predictions
- `update_live_match()` - Real-time updates

---

For more information, see:
- `FOOTBALL_GUIDE.md` - Comprehensive guide
- `README_FOOTBALL.md` - System overview
- `sample_matches.json` - Example input
- `demo.py` - Code examples
