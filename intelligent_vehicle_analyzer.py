"""
Intelligent Vehicle Analysis System
Comprehensive AI-powered vehicle assessment using OpenAI GPT-4o
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from openai import OpenAI

logger = logging.getLogger(__name__)

class IntelligentVehicleAnalyzer:
    """Advanced vehicle analysis using AI and market data"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def analyze_vehicle_comprehensive(self, vehicle_data):
        """Perform comprehensive vehicle analysis with predictions and recommendations"""
        try:
            # Prepare comprehensive data for AI analysis
            analysis_data = self._prepare_analysis_data(vehicle_data)
            
            # Get AI analysis
            ai_analysis = self._get_ai_analysis(analysis_data)
            
            # Get market research data
            market_data = self._get_market_research(vehicle_data)
            
            # Combine all analysis results
            comprehensive_report = {
                'vehicle_info': {
                    'registration': vehicle_data.get('registration'),
                    'make': vehicle_data.get('make'),
                    'model': vehicle_data.get('model'),
                    'year': vehicle_data.get('year'),
                    'analysis_timestamp': datetime.now().isoformat()
                },
                'ai_analysis': ai_analysis,
                'market_analysis': market_data,
                'traffic_light_system': self._generate_traffic_light_system(ai_analysis, market_data)
            }
            
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"Error in comprehensive vehicle analysis: {e}")
            return None
    
    def _prepare_analysis_data(self, vehicle_data):
        """Prepare all available vehicle data for AI analysis"""
        
        # Extract MOT history with detailed analysis
        mot_analysis = self._analyze_mot_patterns(vehicle_data.get('mot_history', {}))
        
        # Extract mileage analysis
        mileage_analysis = self._analyze_mileage_patterns(vehicle_data.get('mileage_history', {}))
        
        # Compile comprehensive data
        analysis_data = {
            'basic_info': {
                'make': vehicle_data.get('make'),
                'model': vehicle_data.get('model'),
                'year': vehicle_data.get('year'),
                'color': vehicle_data.get('color'),
                'fuel_type': vehicle_data.get('fuel_type'),
                'engine_size': vehicle_data.get('engine_size'),
                'transmission': vehicle_data.get('transmission'),
                'body_style': vehicle_data.get('body_style')
            },
            'ownership_data': {
                'total_keepers': vehicle_data.get('total_keepers'),
                'last_v5c_date': vehicle_data.get('last_v5c_issue_date'),
                'registration_place': vehicle_data.get('registration_place')
            },
            'mot_analysis': mot_analysis,
            'mileage_analysis': mileage_analysis,
            'current_status': {
                'mot_expiry': vehicle_data.get('mot_expiry_date'),
                'mot_days_left': vehicle_data.get('mot_days_left'),
                'exported': vehicle_data.get('exported', False),
                'outstanding_recalls': vehicle_data.get('has_outstanding_recall', False)
            }
        }
        
        return analysis_data
    
    def _analyze_mot_patterns(self, mot_history):
        """Analyze MOT history for patterns and predictions"""
        if not mot_history or 'tests' not in mot_history:
            return {'error': 'No MOT history available'}
        
        tests = mot_history.get('tests', [])
        if not tests:
            return {'error': 'No MOT tests found'}
        
        # Analyze failure patterns
        failures = []
        advisories = []
        common_issues = {}
        
        for test in tests:
            if test.get('result', '').upper() == 'FAILED':
                failures.append({
                    'date': test.get('date'),
                    'mileage': test.get('mileage'),
                    'comments': test.get('comments', [])
                })
            
            # Extract advisories and categorize issues
            comments = test.get('comments', [])
            for comment in comments:
                comment_text = comment if isinstance(comment, str) else str(comment)
                
                if 'advisory' in comment_text.lower():
                    advisories.append({
                        'date': test.get('date'),
                        'issue': comment_text,
                        'mileage': test.get('mileage')
                    })
                
                # Categorize common issue types
                issue_category = self._categorize_mot_issue(comment_text)
                if issue_category:
                    common_issues[issue_category] = common_issues.get(issue_category, 0) + 1
        
        return {
            'total_tests': len(tests),
            'failure_count': len(failures),
            'failure_rate': len(failures) / len(tests) if tests else 0,
            'recent_failures': failures[:3],  # Last 3 failures
            'advisory_count': len(advisories),
            'recent_advisories': advisories[:5],  # Last 5 advisories
            'common_issue_categories': common_issues,
            'pattern_analysis': self._detect_mot_patterns(tests)
        }
    
    def _categorize_mot_issue(self, comment):
        """Categorize MOT issues into common problem areas"""
        comment_lower = comment.lower()
        
        categories = {
            'brakes': ['brake', 'braking'],
            'tyres': ['tyre', 'tire'],
            'suspension': ['suspension', 'shock', 'spring'],
            'lights': ['light', 'lamp', 'bulb'],
            'emissions': ['emission', 'exhaust'],
            'steering': ['steering', 'wheel alignment'],
            'bodywork': ['rust', 'corrosion', 'body'],
            'electrical': ['wiring', 'electrical', 'battery']
        }
        
        for category, keywords in categories.items():
            if any(keyword in comment_lower for keyword in keywords):
                return category
        return None
    
    def _detect_mot_patterns(self, tests):
        """Detect patterns in MOT test history"""
        if len(tests) < 3:
            return {'pattern': 'insufficient_data'}
        
        # Analyze test intervals
        intervals = []
        for i in range(1, len(tests)):
            try:
                curr_date = datetime.strptime(tests[i-1]['date'], '%d/%m/%Y')
                prev_date = datetime.strptime(tests[i]['date'], '%d/%m/%Y')
                interval = (curr_date - prev_date).days
                intervals.append(interval)
            except:
                continue
        
        avg_interval = sum(intervals) / len(intervals) if intervals else 365
        
        # Detect deterioration pattern
        recent_tests = tests[:5]  # Last 5 tests
        failure_trend = sum(1 for test in recent_tests if test.get('result', '').upper() == 'FAILED')
        
        return {
            'average_test_interval': round(avg_interval),
            'recent_failure_trend': failure_trend,
            'pattern_detected': 'deteriorating' if failure_trend >= 2 else 'stable'
        }
    
    def _analyze_mileage_patterns(self, mileage_history):
        """Analyze mileage patterns for usage and tampering detection"""
        if not mileage_history or 'mileage_records' not in mileage_history:
            return {'error': 'No mileage history available'}
        
        records = mileage_history.get('mileage_records', [])
        if len(records) < 2:
            return {'error': 'Insufficient mileage data'}
        
        # Calculate annual mileage
        annual_mileages = []
        for i in range(1, len(records)):
            try:
                curr_date = datetime.strptime(records[i-1]['date'], '%d/%m/%Y')
                prev_date = datetime.strptime(records[i]['date'], '%d/%m/%Y')
                days_diff = (curr_date - prev_date).days
                mileage_diff = records[i-1]['mileage'] - records[i]['mileage']
                
                if days_diff > 0 and mileage_diff >= 0:
                    annual_mileage = (mileage_diff / days_diff) * 365
                    annual_mileages.append(annual_mileage)
            except:
                continue
        
        avg_annual_mileage = sum(annual_mileages) / len(annual_mileages) if annual_mileages else 0
        
        return {
            'total_records': len(records),
            'latest_mileage': records[0]['mileage'] if records else 0,
            'average_annual_mileage': round(avg_annual_mileage),
            'usage_category': self._categorize_usage(avg_annual_mileage),
            'mileage_analysis': mileage_history.get('analysis', {}),
            'tampering_detected': mileage_history.get('analysis', {}).get('odometer_issues', {}).get('has_issues', False)
        }
    
    def _categorize_usage(self, annual_mileage):
        """Categorize vehicle usage based on annual mileage"""
        if annual_mileage < 5000:
            return 'low_usage'
        elif annual_mileage < 12000:
            return 'average_usage'
        elif annual_mileage < 20000:
            return 'high_usage'
        else:
            return 'very_high_usage'
    
    def _get_ai_analysis(self, analysis_data):
        """Get comprehensive AI analysis from OpenAI"""
        try:
            system_prompt = """You are an expert automotive analyst with deep knowledge of UK vehicle regulations, MOT requirements, and market conditions. Analyze the provided vehicle data and provide comprehensive insights including:

1. MOT FAILURE PREDICTION:
   - Probability of next MOT failure (percentage)
   - Most likely failure points based on history and common issues
   - Specific components to monitor

2. MAINTENANCE RECOMMENDATIONS:
   - Immediate actions needed
   - Preventive maintenance schedule
   - Cost estimates for common repairs (UK market)

3. RELIABILITY ASSESSMENT:
   - Overall reliability score (1-10)
   - Risk factors and concerns
   - Expected lifespan and maintenance costs

4. PURCHASE RECOMMENDATIONS:
   - Fair market value assessment
   - Price negotiation points
   - Value for money rating

Provide specific, actionable insights based on the vehicle's actual history and current UK market conditions. Include cost estimates in GBP."""

            # Calculate accurate failure probability and CAP valuation
            failure_probability = self._calculate_accurate_failure_probability(analysis_data['mot_analysis'], analysis_data['basic_info'])
            cap_valuation = self._get_cap_based_valuation(analysis_data['basic_info'])

            user_prompt = f"""Analyze this vehicle data with PRECISE calculations based on provided data:

VEHICLE: {analysis_data['basic_info']['make']} {analysis_data['basic_info']['model']} ({analysis_data['basic_info']['year']})

CALCULATED MOT FAILURE PROBABILITY: {failure_probability}% (USE THIS EXACT VALUE)
CAP VALUATION DATA: {json.dumps(cap_valuation, indent=2)}

MOT ANALYSIS:
- Total tests: {analysis_data['mot_analysis'].get('total_tests', 0)}
- Historical failure rate: {analysis_data['mot_analysis'].get('failure_rate', 0):.1%}
- Common issues: {analysis_data['mot_analysis'].get('common_issue_categories', {})}
- Pattern: {analysis_data['mot_analysis'].get('pattern_analysis', {})}

MILEAGE ANALYSIS:
- Current mileage: {analysis_data['mileage_analysis'].get('latest_mileage', 0):,} miles
- Annual average: {analysis_data['mileage_analysis'].get('average_annual_mileage', 0):,} miles
- Usage category: {analysis_data['mileage_analysis'].get('usage_category', 'unknown')}
- Tampering detected: {analysis_data['mileage_analysis'].get('tampering_detected', False)}

OWNERSHIP:
- Total keepers: {analysis_data['ownership_data'].get('total_keepers', 'unknown')}
- Last V5C: {analysis_data['ownership_data'].get('last_v5c_date', 'unknown')}

CURRENT STATUS:
- MOT days left: {analysis_data['current_status'].get('mot_days_left', 'unknown')}
- Exported: {analysis_data['current_status'].get('exported', False)}
- Outstanding recalls: {analysis_data['current_status'].get('outstanding_recalls', False)}

CRITICAL: Use the EXACT failure probability of {failure_probability}% and CAP valuation provided above. Base purchase recommendations on CAP data for accurate UK market values.

Provide detailed analysis with specific predictions and recommendations in valid JSON format."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            else:
                return {'error': 'Empty response from AI'}
            
        except Exception as e:
            logger.error(f"Error getting AI analysis: {e}")
            return {
                'error': 'AI analysis unavailable',
                'message': str(e)
            }
    
    def _get_market_research(self, vehicle_data):
        """Perform market research for vehicle valuation"""
        try:
            make = vehicle_data.get('make', '')
            model = vehicle_data.get('model', '')
            year = vehicle_data.get('year', '')
            
            # Simulate market research (in production, this would query real APIs)
            market_data = {
                'average_price_range': self._estimate_price_range(make, model, year),
                'market_demand': self._assess_market_demand(make, model),
                'depreciation_rate': self._calculate_depreciation(make, year),
                'common_problems': self._get_common_problems(make, model),
                'reliability_rating': self._get_reliability_rating(make, model),
                'parts_availability': self._assess_parts_availability(make),
                'insurance_group': self._estimate_insurance_group(make, model)
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error in market research: {e}")
            return {'error': 'Market research unavailable'}
    
    def _estimate_price_range(self, make, model, year):
        """Estimate price range based on make, model, and year"""
        try:
            current_year = datetime.now().year
            age = current_year - int(year) if year and year.isdigit() else 10
            
            # Base values for different makes (rough estimates)
            base_values = {
                'Audi': 25000,
                'BMW': 28000,
                'Mercedes-Benz': 30000,
                'Ferrari': 150000,
                'Porsche': 60000,
                'Vauxhall': 15000,
                'Ford': 14000,
                'Volkswagen': 18000,
                'Toyota': 16000,
                'Honda': 15000
            }
            
            base_value = base_values.get(make, 12000)
            
            # Apply depreciation
            depreciation_factor = max(0.1, 1 - (age * 0.12))  # 12% per year, minimum 10%
            estimated_value = base_value * depreciation_factor
            
            return {
                'low': int(estimated_value * 0.8),
                'average': int(estimated_value),
                'high': int(estimated_value * 1.2),
                'currency': 'GBP'
            }
            
        except:
            return {'low': 5000, 'average': 8000, 'high': 12000, 'currency': 'GBP'}
    
    def _assess_market_demand(self, make, model):
        """Assess market demand for the vehicle"""
        popular_makes = ['Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Toyota', 'Honda']
        
        if make in popular_makes:
            return {'level': 'high', 'score': 8}
        elif make in ['Ford', 'Vauxhall', 'Nissan']:
            return {'level': 'medium', 'score': 6}
        else:
            return {'level': 'low', 'score': 4}
    
    def _calculate_depreciation(self, make, year):
        """Calculate depreciation rate"""
        try:
            current_year = datetime.now().year
            age = current_year - int(year) if year and year.isdigit() else 10
            
            luxury_makes = ['Ferrari', 'Porsche', 'Aston Martin', 'Lamborghini']
            premium_makes = ['Audi', 'BMW', 'Mercedes-Benz']
            
            if make in luxury_makes:
                base_rate = 8  # Lower depreciation for luxury
            elif make in premium_makes:
                base_rate = 12
            else:
                base_rate = 15
            
            return {
                'annual_rate_percent': base_rate,
                'current_age_years': age,
                'total_depreciation_percent': min(85, age * base_rate)
            }
            
        except:
            return {'annual_rate_percent': 12, 'current_age_years': 10, 'total_depreciation_percent': 60}
    
    def _get_common_problems(self, make, model):
        """Get common problems for the make/model"""
        common_problems = {
            'Audi': ['DPF issues', 'Carbon build-up', 'Timing chain problems'],
            'BMW': ['Oil leaks', 'Cooling system', 'Electronic faults'],
            'Mercedes-Benz': ['Air suspension', 'Electrical issues', 'Rust problems'],
            'Vauxhall': ['Timing chain', 'Water pump', 'Electrical faults'],
            'Ford': ['Clutch problems', 'Cooling system', 'Suspension'],
            'Ferrari': ['Clutch replacement', 'Maintenance costs', 'Parts availability']
        }
        
        return common_problems.get(make, ['General wear items', 'Age-related issues'])
    
    def _get_reliability_rating(self, make, model):
        """Get reliability rating for the make"""
        reliability_scores = {
            'Toyota': 9,
            'Honda': 8,
            'Mazda': 8,
            'Volkswagen': 7,
            'Audi': 7,
            'BMW': 6,
            'Mercedes-Benz': 6,
            'Ford': 6,
            'Vauxhall': 5,
            'Ferrari': 4
        }
        
        score = reliability_scores.get(make, 5)
        return {'score': score, 'max_score': 10}
    
    def _assess_parts_availability(self, make):
        """Assess parts availability"""
        common_makes = ['Ford', 'Vauxhall', 'Volkswagen', 'Audi', 'BMW']
        
        if make in common_makes:
            return {'availability': 'excellent', 'cost_level': 'moderate'}
        elif make in ['Mercedes-Benz', 'Toyota', 'Honda']:
            return {'availability': 'good', 'cost_level': 'moderate'}
        else:
            return {'availability': 'limited', 'cost_level': 'expensive'}
    
    def _estimate_insurance_group(self, make, model):
        """Estimate insurance group"""
        luxury_makes = ['Ferrari', 'Porsche', 'Aston Martin']
        premium_makes = ['Audi', 'BMW', 'Mercedes-Benz']
        
        if make in luxury_makes:
            return {'group': 50, 'level': 'very_high'}
        elif make in premium_makes:
            return {'group': 25, 'level': 'high'}
        else:
            return {'group': 15, 'level': 'moderate'}
    
    def _generate_traffic_light_system(self, ai_analysis, market_data):
        """Generate traffic light system for easy decision making"""
        try:
            # Extract scores from AI analysis
            reliability_score = ai_analysis.get('reliability_assessment', {}).get('overall_score', 5)
            mot_failure_prob = ai_analysis.get('mot_prediction', {}).get('failure_probability', 50)
            
            # Market factors
            market_demand = market_data.get('market_demand', {}).get('score', 5)
            reliability_rating = market_data.get('reliability_rating', {}).get('score', 5)
            
            # Calculate overall scores
            purchase_score = (reliability_score + market_demand + reliability_rating) / 3
            risk_score = mot_failure_prob / 10  # Convert percentage to 1-10 scale
            
            # Generate traffic light recommendations
            traffic_lights = {
                'purchase_recommendation': {
                    'status': 'green' if purchase_score >= 7 else 'amber' if purchase_score >= 5 else 'red',
                    'score': round(purchase_score, 1),
                    'message': self._get_purchase_message(purchase_score)
                },
                'mot_risk': {
                    'status': 'green' if mot_failure_prob < 30 else 'amber' if mot_failure_prob < 60 else 'red',
                    'probability': mot_failure_prob,
                    'message': self._get_mot_risk_message(mot_failure_prob)
                },
                'maintenance_urgency': {
                    'status': self._get_maintenance_status(ai_analysis),
                    'message': self._get_maintenance_message(ai_analysis)
                },
                'value_assessment': {
                    'status': self._get_value_status(market_data, ai_analysis),
                    'message': self._get_value_message(market_data)
                }
            }
            
            return traffic_lights
            
        except Exception as e:
            logger.error(f"Error generating traffic light system: {e}")
            return {'error': 'Traffic light system unavailable'}
    
    def _get_purchase_message(self, score):
        """Get purchase recommendation message"""
        if score >= 7:
            return "Recommended purchase - good reliability and market position"
        elif score >= 5:
            return "Consider carefully - mixed indicators, research further"
        else:
            return "Not recommended - high risk factors identified"
    
    def _get_mot_risk_message(self, probability):
        """Get MOT risk message"""
        if probability < 30:
            return "Low risk - vehicle likely to pass next MOT"
        elif probability < 60:
            return "Moderate risk - some preparation may be needed"
        else:
            return "High risk - significant issues likely, budget for repairs"
    
    def _get_maintenance_status(self, ai_analysis):
        """Get maintenance urgency status"""
        immediate_actions = ai_analysis.get('maintenance_recommendations', {}).get('immediate_actions', [])
        
        if len(immediate_actions) == 0:
            return 'green'
        elif len(immediate_actions) <= 2:
            return 'amber'
        else:
            return 'red'
    
    def _get_maintenance_message(self, ai_analysis):
        """Get maintenance message"""
        immediate_actions = ai_analysis.get('maintenance_recommendations', {}).get('immediate_actions', [])
        
        if len(immediate_actions) == 0:
            return "Minimal maintenance required"
        elif len(immediate_actions) <= 2:
            return f"Some attention needed - {len(immediate_actions)} items"
        else:
            return f"Urgent maintenance required - {len(immediate_actions)} issues"
    
    def _get_value_status(self, market_data, ai_analysis):
        """Get value assessment status"""
        try:
            market_demand = market_data.get('market_demand', {}).get('score', 5)
            reliability = market_data.get('reliability_rating', {}).get('score', 5)
            
            combined_score = (market_demand + reliability) / 2
            
            if combined_score >= 7:
                return 'green'
            elif combined_score >= 5:
                return 'amber'
            else:
                return 'red'
        except:
            return 'amber'
    
    def _get_value_message(self, market_data):
        """Get value assessment message"""
        try:
            price_range = market_data.get('average_price_range', {})
            demand = market_data.get('market_demand', {}).get('level', 'medium')
            
            return f"Market value: £{price_range.get('low', 0):,} - £{price_range.get('high', 0):,}, {demand} demand"
        except:
            return "Value assessment unavailable"
    
    def _calculate_accurate_failure_probability(self, mot_analysis, vehicle_data):
        """Calculate accurate MOT failure probability based on actual vehicle data"""
        base_probability = 25  # UK average MOT failure rate
        
        # Factor 1: Age adjustment
        vehicle_age = 2025 - int(vehicle_data.get('year', 2015))
        if vehicle_age < 5:
            age_factor = 0.7  # Newer cars fail less
        elif vehicle_age < 10:
            age_factor = 1.0  # Average failure rate
        elif vehicle_age < 15:
            age_factor = 1.4  # Higher failure rate
        else:
            age_factor = 1.8  # Much higher failure rate
        
        # Factor 2: Historical failure pattern
        if 'failure_rate' in mot_analysis:
            historical_rate = mot_analysis['failure_rate'] * 100
            history_factor = historical_rate / 25  # Normalize to UK average
        else:
            history_factor = 1.0
        
        # Factor 3: Recent trend
        pattern_factor = 1.0
        if 'pattern_analysis' in mot_analysis:
            if mot_analysis['pattern_analysis'].get('pattern_detected') == 'deteriorating':
                pattern_factor = 1.5
            elif mot_analysis['pattern_analysis'].get('recent_failure_trend', 0) >= 2:
                pattern_factor = 1.3
        
        # Factor 4: Make/model reliability
        make = vehicle_data.get('make', '').lower()
        reliability_factor = self._get_make_reliability_factor(make)
        
        # Calculate final probability
        final_probability = base_probability * age_factor * history_factor * pattern_factor * reliability_factor
        
        # Cap between 5% and 85%
        return max(5, min(85, round(final_probability)))
    
    def _get_make_reliability_factor(self, make):
        """Get reliability factor based on vehicle make"""
        reliability_map = {
            'toyota': 0.7, 'honda': 0.75, 'mazda': 0.8, 'nissan': 0.85,
            'ford': 1.0, 'vauxhall': 1.1, 'volkswagen': 0.9, 'audi': 0.95,
            'bmw': 1.1, 'mercedes': 1.05, 'peugeot': 1.2, 'citroen': 1.2,
            'renault': 1.15, 'fiat': 1.3, 'alfa romeo': 1.4, 'jaguar': 1.3,
            'land rover': 1.4, 'mini': 1.0, 'skoda': 0.9, 'seat': 1.0
        }
        return reliability_map.get(make, 1.0)
    
    def _get_cap_based_valuation(self, vehicle_data):
        """Get CAP-based valuation estimate"""
        make = vehicle_data.get('make', '')
        model = vehicle_data.get('model', '')
        year = int(vehicle_data.get('year', 2015))
        
        # Base values by age and make (simplified CAP approximation)
        age = 2025 - year
        
        # Base value calculation
        if age < 3:
            base_multiplier = 0.65  # Retain 65% of new value
        elif age < 6:
            base_multiplier = 0.45  # Retain 45% of new value
        elif age < 10:
            base_multiplier = 0.25  # Retain 25% of new value
        elif age < 15:
            base_multiplier = 0.15  # Retain 15% of new value
        else:
            base_multiplier = 0.08  # Retain 8% of new value
        
        # Estimated new values by make/model category
        new_value_estimates = {
            'ferrari': 180000, 'lamborghini': 200000, 'porsche': 80000,
            'mercedes': 45000, 'bmw': 42000, 'audi': 40000, 'jaguar': 50000,
            'land rover': 45000, 'volkswagen': 28000, 'ford': 22000,
            'vauxhall': 20000, 'toyota': 25000, 'honda': 24000, 'nissan': 23000,
            'peugeot': 21000, 'citroen': 20000, 'renault': 20000, 'fiat': 18000
        }
        
        make_lower = make.lower()
        estimated_new_value = new_value_estimates.get(make_lower, 22000)
        
        # Calculate depreciated value
        current_value = estimated_new_value * base_multiplier
        
        return {
            'cap_estimate': round(current_value),
            'trade_value': round(current_value * 0.8),  # Trade price typically 80% of retail
            'retail_high': round(current_value * 1.15),  # Retail high
            'retail_low': round(current_value * 0.9),   # Retail low
            'confidence': 'medium' if age < 15 else 'low'
        }