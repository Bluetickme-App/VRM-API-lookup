"""
Enhanced MOT Failure Analysis System
Provides specific component failure predictions and repeat failure likelihood analysis
"""

import openai
import json
import logging
from datetime import datetime, timedelta
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedFailureAnalyzer:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    def analyze_specific_failures(self, vehicle_data):
        """
        Analyze specific MOT failure causes and predict repeat failure likelihood
        """
        try:
            # Extract MOT history for analysis
            mot_history = vehicle_data.get('mot_history', {})
            tests = mot_history.get('tests', []) if isinstance(mot_history, dict) else []
            
            if not tests:
                logger.warning("No MOT tests found for failure analysis")
                return self._generate_empty_predictions()
            
            # Create focused prompt for failure predictions
            prompt = self._create_failure_analysis_prompt(vehicle_data, tests)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a UK MOT specialist focusing on component failure prediction and repeat failure analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            if content:
                content = content.strip()
            logger.info(f"Enhanced failure analysis generated: {len(content)} characters")
            
            # Parse JSON response
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            
            analysis = json.loads(content)
            return analysis
            
        except Exception as e:
            logger.error(f"Enhanced failure analysis error: {str(e)}")
            return self._generate_empty_predictions()
    
    def _create_failure_analysis_prompt(self, vehicle_data, tests):
        """Create focused prompt for failure analysis"""
        
        # Extract vehicle details
        make = vehicle_data.get('make', 'Unknown')
        model = vehicle_data.get('model', 'Unknown') 
        year = vehicle_data.get('year', 'Unknown')
        
        # Analyze failed tests
        failed_tests = []
        for test in tests:
            if test.get('result', '').upper() == 'FAIL':
                failed_tests.append({
                    'date': test.get('date', 'Unknown'),
                    'mileage': test.get('mileage', 0),
                    'comments': test.get('comments', [])
                })
        
        prompt = f"""
VEHICLE: {make} {model} ({year})
TOTAL MOT TESTS: {len(tests)}
FAILED TESTS: {len(failed_tests)}

FAILED TEST DETAILS:
"""
        
        for i, failure in enumerate(failed_tests[-5:]):  # Last 5 failures
            prompt += f"""
FAILURE {i+1}:
Date: {failure['date']}
Mileage: {failure['mileage']}
Defects: {failure['comments'][:3]}  # Top 3 defects
"""
        
        prompt += """
ANALYSIS REQUIREMENTS:
1. Identify specific components that have failed in MOT tests
2. For each failed component, predict likelihood of repeat failure if not properly repaired
3. Provide timeline estimates for when components might fail again
4. Give specific prevention actions and repair costs

Generate JSON response with this structure:
{
  "specific_predictions": [
    {
      "component": "exact component name (e.g. 'Nearside front brake disc')",
      "last_failure_date": "date of most recent failure",
      "failure_cause": "exact defect description from MOT",
      "repeat_probability": 85,
      "predicted_failure_date": "estimated next failure date",
      "prevention_action": "specific repair needed",
      "estimated_cost": 150
    }
  ],
  "repeat_failure_risk": {
    "high_risk_components": ["components likely to fail again"],
    "failure_timeline": ["when each will likely fail"],
    "prevention_cost": 500
  },
  "failure_probability": 25,
  "next_test_date": "next MOT due date"
}
"""
        return prompt
    
    def _generate_empty_predictions(self):
        """Generate empty predictions structure when no data available"""
        return {
            "specific_predictions": [],
            "repeat_failure_risk": {
                "high_risk_components": [],
                "failure_timeline": [],
                "prevention_cost": 0
            },
            "failure_probability": 0,
            "next_test_date": "Unknown"
        }

def analyze_vehicle_failures(vehicle_data):
    """Main function to analyze vehicle failures"""
    analyzer = EnhancedFailureAnalyzer()
    return analyzer.analyze_specific_failures(vehicle_data)