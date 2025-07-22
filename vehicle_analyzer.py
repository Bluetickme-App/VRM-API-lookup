"""
Vehicle Analysis System using OpenAI GPT-4o
Provides intelligent MOT predictions, risk assessment, and trade recommendations
"""

import json
import os
from datetime import datetime
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)


def analyze_vehicle_data(vehicle_data):
    """
    Analyze vehicle data using OpenAI GPT-4o for comprehensive assessment
    Returns structured analysis with MOT predictions, risk assessment, and trade recommendations
    """
    try:
        # Prepare the vehicle data for analysis
        analysis_prompt = create_analysis_prompt(vehicle_data)
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": get_system_prompt()
                },
                {
                    "role": "user", 
                    "content": analysis_prompt
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.1  # Low temperature for consistent analysis
        )
        
        content = response.choices[0].message.content
        if content is None:
            raise Exception("OpenAI response content is empty")
        analysis_result = json.loads(content)
        
        # Add metadata
        analysis_result["analysis_metadata"] = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "model_used": "gpt-4o",
            "analysis_version": "1.0"
        }
        
        return analysis_result
        
    except Exception as e:
        return {
            "error": f"Failed to analyze vehicle data: {str(e)}",
            "analysis_metadata": {
                "analyzed_at": datetime.utcnow().isoformat(),
                "error": True
            }
        }


def get_system_prompt():
    """
    System prompt for the vehicle reliability analyst
    """
    return """You are a vehicle reliability and MOT advisory analyst focused on UK vehicles. You analyze authentic DVLA vehicle data including comprehensive MOT history, accurate mileage progression, wear patterns, tax/MOT compliance status, and mechanical condition grading.

IMPORTANT: All vehicles will have complete MOT and mileage history from DVLA sources. There are no cases of missing data.

Your analysis tasks:
1. Analyze complete MOT test history for wear/neglect patterns
2. Predict likely MOT failure areas based on historical advisories and failures
3. Estimate maintenance costs using realistic UK garage pricing (£200-£2000 range)
4. Assign mechanical risk bands: Low (Grade A-B), Moderate (Grade C), High (Grade D-E)
5. Provide trade purchase recommendations with CAP pricing tiers
6. Analyze mileage progression for anomalies or tampering signs

Focus on recurring advisories (brakes, tyres, suspension) and escalating faults. Consider vehicle age, mileage appropriateness, and compliance status in your assessment.

Output must be structured JSON using this schema:
{
  "vehicle_summary": {
    "registration": "string",
    "age_years": "number",
    "total_mot_tests": "number",
    "last_mot_result": "string"
  },
  "mileage_analysis": {
    "current_mileage": "number",
    "annual_average": "number",
    "mileage_anomalies": ["string"],
    "mileage_risk": "Low|Moderate|High"
  },
  "mot_pattern_analysis": {
    "repeated_advisories": ["string"],
    "failure_patterns": ["string"],
    "wear_indicators": ["string"],
    "compliance_status": "Current|Expired|Unknown"
  },
  "risk_assessment": {
    "overall_risk": "Low|Moderate|High",
    "mechanical_grade": "A|B|C|D|E",
    "risk_factors": ["string"],
    "positive_indicators": ["string"]
  },
  "mot_predictions": {
    "next_test_date": "string",
    "failure_probability": "number (0-100)",
    "likely_failure_areas": ["string"],
    "recommended_pre_mot_work": ["string"]
  },
  "cost_estimates": {
    "immediate_repairs": "number",
    "pre_mot_work": "number", 
    "annual_maintenance": "number",
    "total_first_year": "number"
  },
  "trade_recommendation": {
    "purchase_advice": "Buy|Avoid|Caution",
    "cap_pricing_tier": "CAP Clean|CAP Average|CAP Below",
    "trade_value_factors": ["string"],
    "profit_potential": "High|Medium|Low"
  },
  "ownership_analysis": {
    "v5_changes_detected": "boolean",
    "trading_indicators": ["string"],
    "auction_risk_factors": ["string"]
  }
}"""


def create_analysis_prompt(vehicle_data):
    """
    Create the analysis prompt with structured vehicle data from raw_data
    """
    registration = vehicle_data.get('registration', 'Unknown')
    year = vehicle_data.get('year', 'Unknown')
    make = vehicle_data.get('make', 'Unknown')
    model = vehicle_data.get('model', 'Unknown')
    
    # MOT History Analysis - data already extracted in intelligent_analysis_api.py
    mot_history = vehicle_data.get('mot_history', {})
    mileage_history = vehicle_data.get('mileage_history', {})
    
    mot_tests = mot_history.get('mot_tests', [])
    mileage_records = mileage_history.get('mileage_records', [])
    
    print(f"DEBUG: Found {len(mot_tests)} MOT tests for {registration}")
    if mot_tests:
        first_test = mot_tests[0]
        print(f"DEBUG: First test has comments: {bool(first_test.get('comments'))}")
        if first_test.get('comments'):
            print(f"DEBUG: Comment type: {type(first_test['comments'])}, Count: {len(first_test['comments']) if isinstance(first_test['comments'], list) else 'N/A'}")
    
    # Current date for age calculation
    current_year = datetime.now().year
    vehicle_age = current_year - int(year) if year != 'Unknown' and year else 0
    
    prompt = f"""
AUTHENTIC DVLA VEHICLE DATA FOR ANALYSIS:

BASIC INFORMATION:
- Registration: {registration}
- Make/Model: {make} {model}
- Year: {year} (Age: {vehicle_age} years)
- Color: {vehicle_data.get('color', 'Unknown')}
- Fuel Type: {vehicle_data.get('fuel_type', 'Unknown')}

COMPLETE MOT TEST HISTORY ({len(mot_tests)} authentic DVLA tests):
"""
    
    # Add complete MOT test details with all defects and advisories
    for i, test in enumerate(mot_tests[:12]):  # Include more tests for better pattern analysis
        test_date = test.get('test_date', 'Unknown')
        result = test.get('result', 'Unknown')
        mileage = test.get('mileage', 'Unknown')
        
        # Extract all defect categories and comments (handle both formats)
        defects = test.get('defects', [])
        advisories = test.get('advisories', [])
        minor_defects = test.get('minor_defects', [])
        major_defects = test.get('major_defects', [])
        dangerous_defects = test.get('dangerous_defects', [])
        
        # Handle comments - can be string or list of comment objects
        comments = test.get('comments', [])
        full_comments = ''
        comment_details = []
        
        if isinstance(comments, list):
            for comment in comments:
                if isinstance(comment, dict):
                    comment_text = comment.get('text', '')
                    comment_type = comment.get('type', 'UNKNOWN')
                    comment_details.append(f"{comment_type}: {comment_text}")
                else:
                    comment_details.append(str(comment))
            full_comments = '; '.join(comment_details)
        else:
            full_comments = str(comments)
        
        test_details = test.get('test_details', '')
        
        # Format mileage properly (handle both string and numeric)
        if isinstance(mileage, (int, float)):
            mileage_display = f"{mileage:,} miles"
        else:
            mileage_display = f"{mileage} miles"
        
        prompt += f"""
Test {i+1}: {test_date}
- Result: {result}
- Mileage: {mileage_display}
- Full Test Details: {full_comments}
"""
        
        # Add all defect categories with complete information
        if defects:
            prompt += f"- General Defects: {'; '.join(defects)}\n"
        if advisories:
            prompt += f"- Advisories: {'; '.join(advisories)}\n"
        if minor_defects:
            prompt += f"- Minor Defects: {'; '.join(minor_defects)}\n"
        if major_defects:
            prompt += f"- Major Defects: {'; '.join(major_defects)}\n"
        if dangerous_defects:
            prompt += f"- Dangerous Defects: {'; '.join(dangerous_defects)}\n"
        if test_details:
            prompt += f"- Additional Details: {test_details}\n"
    
    # Add comprehensive mileage progression with anomaly detection
    prompt += f"\nCOMPLETE MILEAGE HISTORY ({len(mileage_records)} authentic DVLA records):\n"
    
    # Include mileage summary and analysis if available
    mileage_summary = mileage_history.get('summary', {})
    if mileage_summary:
        prompt += f"MILEAGE SUMMARY:\n"
        
        # Format current mileage
        current_mileage = mileage_summary.get('current_mileage', 'Unknown')
        if isinstance(current_mileage, (int, float)):
            current_mileage_str = f"{current_mileage:,}"
        else:
            current_mileage_str = str(current_mileage)
        
        # Format annual average
        annual_avg = mileage_summary.get('annual_average', 'Unknown')
        if isinstance(annual_avg, (int, float)):
            annual_avg_str = f"{annual_avg:,}"
        else:
            annual_avg_str = str(annual_avg)
        
        # Format total increase
        total_increase = mileage_summary.get('total_increase', 'Unknown')
        if isinstance(total_increase, (int, float)):
            total_increase_str = f"{total_increase:,}"
        else:
            total_increase_str = str(total_increase)
        
        prompt += f"- Current Mileage: {current_mileage_str} miles\n"
        prompt += f"- Annual Average: {annual_avg_str} miles/year\n"
        prompt += f"- Total Increase: {total_increase_str} miles\n"
        
        # Include any mileage warnings or anomalies
        mileage_warnings = mileage_summary.get('warnings', [])
        if mileage_warnings:
            prompt += f"- MILEAGE WARNINGS: {'; '.join(mileage_warnings)}\n"
        
        mileage_anomalies = mileage_summary.get('anomalies', [])
        if mileage_anomalies:
            prompt += f"- MILEAGE ANOMALIES: {'; '.join(mileage_anomalies)}\n"
    
    prompt += f"\nDETAILED MILEAGE PROGRESSION:\n"
    for i, record in enumerate(mileage_records[:10]):  # Include more records for better analysis
        date = record.get('date', 'Unknown')
        mileage = record.get('mileage', 'Unknown')
        source = record.get('source', 'MOT')
        
        # Format mileage with proper number handling
        if isinstance(mileage, (int, float)):
            mileage_str = f"{mileage:,}"
        else:
            # Try to convert string to int for formatting
            try:
                mileage_num = int(str(mileage).replace(',', ''))
                mileage_str = f"{mileage_num:,}"
            except (ValueError, TypeError):
                mileage_str = str(mileage)
        
        # Calculate mileage increase if possible
        if i > 0 and isinstance(mileage, (int, float)) and isinstance(mileage_records[i-1].get('mileage'), (int, float)):
            increase = mileage - mileage_records[i-1].get('mileage', 0)
            prompt += f"- {date}: {mileage_str} miles (Source: {source}) [+{increase:,} miles]\n"
        else:
            prompt += f"- {date}: {mileage_str} miles (Source: {source})\n"
    
    # Add compliance status
    prompt += f"""
COMPLIANCE STATUS:
- Tax Status: {vehicle_data.get('tax_status', 'Unknown')}
- MOT Status: {vehicle_data.get('mot_status', 'Unknown')}
- Last MOT: {vehicle_data.get('mot_expiry', 'Unknown')}

ADDITIONAL INFORMATION:
- Engine Size: {vehicle_data.get('engine_size', 'Unknown')}
- CO2 Emissions: {vehicle_data.get('co2_emissions', 'Unknown')}
- Date First Registered: {vehicle_data.get('date_first_registered', 'Unknown')}

Please analyze this vehicle data and provide a comprehensive assessment following the required JSON schema. Focus on identifying patterns, predicting future issues, and providing actionable trade recommendations.
"""
    
    return prompt


def format_analysis_for_display(analysis_result):
    """
    Format the analysis result for web display
    """
    if "error" in analysis_result:
        return {
            "success": False,
            "error": analysis_result["error"],
            "display_data": None
        }
    
    try:
        # Extract key information for display
        display_data = {
            "overall_assessment": {
                "risk_level": analysis_result.get("risk_assessment", {}).get("overall_risk", "Unknown"),
                "mechanical_grade": analysis_result.get("risk_assessment", {}).get("mechanical_grade", "Unknown"),
                "trade_advice": analysis_result.get("trade_recommendation", {}).get("purchase_advice", "Unknown"),
                "cap_tier": analysis_result.get("trade_recommendation", {}).get("cap_pricing_tier", "Unknown")
            },
            "mot_predictions": {
                "failure_probability": analysis_result.get("mot_predictions", {}).get("failure_probability", 0),
                "likely_failures": analysis_result.get("mot_predictions", {}).get("likely_failure_areas", []),
                "recommended_work": analysis_result.get("mot_predictions", {}).get("recommended_pre_mot_work", [])
            },
            "cost_breakdown": {
                "immediate_repairs": analysis_result.get("cost_estimates", {}).get("immediate_repairs", 0),
                "pre_mot_work": analysis_result.get("cost_estimates", {}).get("pre_mot_work", 0),
                "annual_maintenance": analysis_result.get("cost_estimates", {}).get("annual_maintenance", 0),
                "total_first_year": analysis_result.get("cost_estimates", {}).get("total_first_year", 0)
            },
            "risk_factors": analysis_result.get("risk_assessment", {}).get("risk_factors", []),
            "positive_indicators": analysis_result.get("risk_assessment", {}).get("positive_indicators", []),
            "mileage_analysis": analysis_result.get("mileage_analysis", {}),
            "pattern_analysis": analysis_result.get("mot_pattern_analysis", {}),
            "ownership_analysis": analysis_result.get("ownership_analysis", {})
        }
        
        return {
            "success": True,
            "error": None,
            "display_data": display_data,
            "raw_analysis": analysis_result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to format analysis: {str(e)}",
            "display_data": None
        }