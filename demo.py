#!/usr/bin/env python3
"""
Football Prediction Analyzer - Examples & Demo

This script demonstrates various ways to use the football prediction system.
"""

import json
from app.football_main import predict_match
from datetime import datetime


def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def example_1_single_prediction():
    """Example 1: Single match prediction"""
    print_header("EXAMPLE 1: Single Match Prediction")
    
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
        "time": "00:00",
        "prediction": "",
        "reason": ""
    }
    
    print("Input match data:")
    print(json.dumps(match, indent=2))
    
    result = predict_match(match)
    
    print("\nKey prediction fields:")
    key_fields = {
        "Match": f"{result['homeTeam']} vs {result['awayTeam']}",
        "Prediction": result['prediction'],
        "Confidence": f"{result['confidence_score']}%",
        "Expected Score": result['expected_score'],
        "Risk Level": result['risk_level'],
        "Value Rating": f"{result['value_rating']}/5"
    }
    for k, v in key_fields.items():
        print(f"  {k}: {v}")


def example_2_detailed_analysis():
    """Example 2: Detailed prediction analysis"""
    print_header("EXAMPLE 2: Detailed Analysis - All Fields")
    
    match = {
        "homeTeam": "Argentina",
        "awayTeam": "Senegal",
        "date": "2026-06-21",
        "league": "FIFA World Cup",
        "id": "537355",
        "livescoreId": "537355",
        "markets": "1X2",
        "matchStatus": "Not Started",
        "type": "premium",
        "status": "pending",
        "score": "0-0",
        "time": "12:00"
    }
    
    result = predict_match(match)
    
    print("📊 MATCH INFORMATION")
    print(f"  Date: {result['date']} at {result['time']}")
    print(f"  League: {result['league']}")
    print(f"  Status: {result['matchStatus']}")
    
    print("\n🎯 MAIN PREDICTION")
    print(f"  Market: {result['basic_prediction']['market']}")
    print(f"  Prediction: {result['basic_prediction']['prediction']}")
    print(f"  Confidence: {result['basic_prediction']['confidence']}%")
    print(f"  Reason: {result['basic_prediction']['reason']}")
    
    print("\n📈 PROBABILITY ANALYSIS")
    probs = result['win_probabilities']
    print(f"  Home Win: {probs['home']}%")
    print(f"  Draw: {probs['draw']}%")
    print(f"  Away Win: {probs['away']}%")
    
    print("\n⚽ EXPECTED GOALS")
    xg = result['expected_goals']
    print(f"  Home xG: {xg['home']}")
    print(f"  Away xG: {xg['away']}")
    print(f"  Expected Score: {result['expected_score']}")
    
    print("\n💪 TEAM FORM")
    form = result['form']
    print(f"  Home Form (last 5): {form['home']}")
    print(f"  Away Form (last 5): {form['away']}")
    
    print("\n🏆 HEAD-TO-HEAD HISTORY")
    h2h = result['h2h_summary']
    print(f"  Matches Played: {h2h['played']}")
    print(f"  Home Wins: {h2h['home_wins']}")
    print(f"  Draws: {h2h['draws']}")
    print(f"  Away Wins: {h2h['away_wins']}")
    print(f"  Average Goals: {h2h['avg_goals']}")
    
    print("\n⚠️ INJURY ALERTS")
    injury = result['injury_alert']
    print(f"  Active: {injury['active']}")
    if injury['home_team']:
        print(f"  Home Team Issues: {injury['home_team']}")
    if injury['away_team']:
        print(f"  Away Team Issues: {injury['away_team']}")
    
    print("\n🔑 KEY FACTORS")
    for i, factor in enumerate(result['key_factors'], 1):
        print(f"  {i}. {factor}")
    
    print("\n💰 RISK & VALUE")
    print(f"  Risk Level: {result['risk_level']}")
    print(f"  Value Rating: {result['value_rating']}/5 stars")
    print(f"  Overall Confidence: {result['confidence_score']}%")
    
    print("\n📋 MULTIPLE PREDICTION TIERS")
    print(f"\n  Basic Prediction:")
    basic = result['basic_prediction']
    print(f"    Market: {basic['market']}")
    print(f"    Prediction: {basic['prediction']}")
    print(f"    Confidence: {basic['confidence']}%")
    
    print(f"\n  Premium Prediction:")
    premium = result['premium_prediction']
    print(f"    Market: {premium['market']}")
    print(f"    Prediction: {premium['prediction']}")
    print(f"    Confidence: {premium['confidence']}%")
    
    print(f"\n  Alternative Tip:")
    alt = result['alternative_tip']
    print(f"    Market: {alt['market']}")
    print(f"    Prediction: {alt['prediction']}")
    print(f"    Confidence: {alt['confidence']}%")


def example_3_comparison():
    """Example 3: Compare multiple matches"""
    print_header("EXAMPLE 3: Comparing Multiple Matches")
    
    matches = [
        {
            "homeTeam": "France",
            "awayTeam": "Belgium",
            "date": "2026-06-22",
            "league": "FIFA World Cup",
            "id": "537356",
            "livescoreId": "537356",
        },
        {
            "homeTeam": "Germany",
            "awayTeam": "Spain",
            "date": "2026-06-22",
            "league": "FIFA World Cup",
            "id": "537357",
            "livescoreId": "537357",
        },
        {
            "homeTeam": "Brazil",
            "awayTeam": "Italy",
            "date": "2026-06-22",
            "league": "FIFA World Cup",
            "id": "537358",
            "livescoreId": "537358",
        }
    ]
    
    print("Predictions Summary:\n")
    print(f"{'Match':<25} {'Prediction':<20} {'Confidence':<12} {'Risk':<10} {'xG':<10}")
    print("-" * 80)
    
    for match in matches:
        result = predict_match(match)
        match_name = f"{result['homeTeam']} vs {result['awayTeam']}"
        xg_total = result['expected_goals']['home'] + result['expected_goals']['away']
        
        print(
            f"{match_name:<25} "
            f"{result['prediction']:<20} "
            f"{result['confidence_score']:<12}% "
            f"{result['risk_level']:<10} "
            f"{xg_total:<10.1f}"
        )


def example_4_export_json():
    """Example 4: Export prediction to JSON file"""
    print_header("EXAMPLE 4: Export to JSON")
    
    match = {
        "homeTeam": "England",
        "awayTeam": "Netherlands",
        "date": "2026-06-25",
        "league": "FIFA World Cup",
        "id": "537359",
        "livescoreId": "537359",
    }
    
    result = predict_match(match)
    
    filename = "england_vs_netherlands_prediction.json"
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Prediction exported to: {filename}")
    print(f"\nFile size: {len(json.dumps(result, indent=2))} bytes")
    print(f"Total fields: {len(result)}")


def main():
    print("\n")
    print("  FOOTBALL PREDICTION ANALYZER - EXAMPLES & DEMOS")
    print("  " + "=" * 60)
    print("  Transform your research agent into a sports analysis tool")
    print("  " + "=" * 60)
    
    try:
        example_1_single_prediction()
        example_2_detailed_analysis()
        example_3_comparison()
        example_4_export_json()
        
        print("ALL EXAMPLES COMPLETED - OK")
        print("For batch predictions, run: python app/football_main.py sample_matches.json")
        print("For detailed documentation, see: FOOTBALL_GUIDE.md")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
