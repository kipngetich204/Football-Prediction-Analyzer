# Football Prediction Analyzer - Usage Guide

## Overview
This system transforms the Autonomous Research Agent into a sophisticated football prediction analyzer. It accepts match data and generates comprehensive predictions with detailed analysis.

## Quick Start

### Single Match Prediction
```python
from app.football_main import predict_match
import json

match_data = {
    "awayTeam": "Curaçao",
    "date": "2026-06-20",
    "homeTeam": "Ecuador",
    "id": "537354",
    "league": "FIFA World Cup",
    "livescoreId": "537354",
    "markets": "Over 2.5 Goals",
    "matchStatus": "Not Started",
    "prediction": "",
    "reason": "",
    "score": "0-0",
    "status": "pending",
    "time": "00:00",
    "type": "basic"
}

result = predict_match(match_data)
print(json.dumps(result, indent=2))
```

### Command Line Usage

**Single Match:**
```bash
cd "c:\Users\kipng\Web\Autonomous Research Agent"
python app/football_main.py
```

**Batch Predictions (from JSON file):**
```bash
python app/football_main.py matches.json
```

## Input Format

The system accepts match data with these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Match ID |
| livescoreId | string | Yes | Livescore reference ID |
| date | string | Yes | Match date (YYYY-MM-DD) |
| league | string | Yes | League/Tournament name |
| homeTeam | string | Yes | Home team name |
| awayTeam | string | Yes | Away team name |
| time | string | No | Match time (HH:MM) |
| score | string | No | Current score |
| matchStatus | string | No | Not Started, Live, or Finished |
| markets | string | No | Betting market (Over 2.5 Goals, GG, 1X2, etc.) |
| type | string | No | basic, premium, or super-premium |
| status | string | No | pending, won, or lost |

## Output Format

The system generates predictions with comprehensive analysis:

### Core Prediction Fields
- **prediction**: Main prediction (e.g., "Over 2.5 Goals")
- **reason**: Reasoning behind the prediction
- **confidence_score**: 0-100 confidence level
- **expected_score**: Predicted final score (e.g., "2-1")

### Probability Analysis
```json
"win_probabilities": {
  "home": 56,      // Home win probability
  "draw": 35,      // Draw probability
  "away": 8        // Away win probability
}
```

### Expected Goals (xG)
```json
"expected_goals": {
  "home": 2.5,     // Home team xG
  "away": 2.1      // Away team xG
}
```

### Team Form
```json
"form": {
  "home": "WWWDL",  // Recent wins, draws, losses
  "away": "LWWDD"   // L=Loss, W=Win, D=Draw
}
```

### Head-to-Head Summary
```json
"h2h_summary": {
  "played": 10,
  "home_wins": 6,
  "draws": 2,
  "away_wins": 2,
  "avg_goals": 2.8,
  "last_meeting": "date or null"
}
```

### Prediction Tiers

1. **basic_prediction** - Simple market prediction (Over/Under, BTTS, etc.)
2. **premium_prediction** - Enhanced prediction (Both Teams to Score, etc.)
3. **super_premium_prediction** - Optional advanced prediction
4. **alternative_tip** - Alternative market suggestion

### Risk Assessment
- **risk_level**: Low | Medium | High
- **value_rating**: 1-5 stars
- **match_importance**: Low | Medium | High | Critical

### Injury Alerts
```json
"injury_alert": {
  "active": false,
  "home_team": null,
  "away_team": null
}
```

## System Components

### Football Prediction Agent (`agent/football_agent.py`)
Main orchestrator that:
- Analyzes match data
- Gathers team statistics
- Analyzes form and H2H history
- Generates comprehensive predictions
- Calculates win probabilities and xG

### Football Tools (`tools/football_tools.py`)
- **team_stats**: Team performance metrics
- **head_to_head**: H2H history analysis
- **form_analysis**: Recent form and momentum
- **injury_data**: Injury and suspension info

### Data Models (`agent/football_models.py`)
- `FootballPredictionOutput`: Complete prediction schema
- Supporting models for probabilities, form, H2H, etc.

### Entry Point (`app/football_main.py`)
- `predict_match()`: Single match prediction
- `batch_predict()`: Multiple match predictions

## Example: Complete Workflow

```python
from app.football_main import predict_match, batch_predict
import json

# Predict single match
match = {
    "homeTeam": "Ecuador",
    "awayTeam": "Curaçao",
    "date": "2026-06-20",
    "league": "FIFA World Cup",
    "id": "537354",
    "livescoreId": "537354",
    "markets": "Over 2.5 Goals",
    "matchStatus": "Not Started",
    "type": "basic",
    "status": "pending",
    "score": "0-0",
    "time": "00:00"
}

prediction = predict_match(match)

# Key outputs
print(f"Prediction: {prediction['prediction']}")
print(f"Confidence: {prediction['confidence_score']}%")
print(f"Expected Score: {prediction['expected_score']}")
print(f"Risk Level: {prediction['risk_level']}")
print(f"Win Probability (Home): {prediction['win_probabilities']['home']}%")
```

## Advanced Features

### Custom Analysis Triggers
The system automatically:
1. Fetches team statistics from mock database
2. Analyzes head-to-head history
3. Evaluates recent form (last 5 matches)
4. Checks for injury alerts
5. Calculates Poisson-based probabilities
6. Generates expected goals (xG)

### Extensibility
To add new tools:
1. Create tool class inheriting from `BaseTool`
2. Define `args_schema` with Pydantic model
3. Implement `run()` method
4. Register in `FootballPredictionAgent.__init__()`

Example:
```python
from tools.base import BaseTool
from pydantic import BaseModel

class MyToolArgs(BaseModel):
    param: str

class MyTool(BaseTool):
    name = "my_tool"
    description = "Tool description"
    args_schema = MyToolArgs
    
    def run(self, args: MyToolArgs) -> str:
        # Implementation
        return json.dumps(result)

# Register in football_agent.py
self.registry.register(MyTool())
```

## Output Files

- `prediction_output.json`: Single prediction result
- `predictions_batch.json`: Batch predictions result
- `trajectories/`: Agent execution logs (if using research mode)

## Notes

- All probabilities are normalized to 100%
- Expected goals are bounded 0.3-4.0
- Win probability calculations include home advantage (0.3 bonus)
- Form strings use: W=Win, D=Draw, L=Loss (most recent first)
- Mock data is used for demonstration (connect to real APIs as needed)

## Future Enhancements

1. Integration with live sports APIs (ESPN, API Football, etc.)
2. Machine learning models for probability prediction
3. Real-time injury/suspension updates
4. Weather and pitch condition analysis
5. Player-level statistics integration
6. Betting odds comparison
7. Historical prediction accuracy tracking
