"""
Data extraction module for processing vehicle information from web pages
Handles parsing of different data sections and formats
"""

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import re
import logging

logger = logging.getLogger(__name__)

class DataExtractor:
    """Handles extraction of vehicle data from web pages"""
    
    def extract_all_data(self, driver):
        """Extract comprehensive vehicle data from the page"""
        try:
            vehicle_data = {}
            
            # Extract basic vehicle information
            vehicle_data['basic_info'] = self._extract_basic_info(driver)
            
            # Extract tax and MOT information
            vehicle_data['tax_mot'] = self._extract_tax_mot_info(driver)
            
            # Extract vehicle details table
            vehicle_data['vehicle_details'] = self._extract_vehicle_details(driver)
            
            # Extract mileage information
            vehicle_data['mileage'] = self._extract_mileage_info(driver)
            
            # Extract performance data
            vehicle_data['performance'] = self._extract_performance_data(driver)
            
            # Extract fuel economy
            vehicle_data['fuel_economy'] = self._extract_fuel_economy(driver)
            
            # Extract safety ratings
            vehicle_data['safety'] = self._extract_safety_ratings(driver)
            
            # Extract additional information including total keepers
            vehicle_data['additional'] = self._extract_additional_info(driver)
            
            # Extract total keepers using specific XPath
            try:
                total_keepers_element = driver.find_element(By.XPATH, "/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[5]/div[2]/div/div[1]/div[2]")
                total_keepers_text = total_keepers_element.text.strip()
                if total_keepers_text and total_keepers_text.isdigit():
                    if 'additional' not in vehicle_data:
                        vehicle_data['additional'] = {}
                    vehicle_data['additional']['total_keepers'] = int(total_keepers_text)
                    logger.info(f"Extracted total keepers: {total_keepers_text}")
            except Exception as e:
                logger.debug(f"Total keepers XPath extraction failed: {e}")
                
                # Try alternative extraction from page text
                try:
                    page_text = driver.page_source.lower()
                    keepers_match = re.search(r'total keepers[:\s]*(\d+)', page_text, re.IGNORECASE)
                    if keepers_match:
                        if 'additional' not in vehicle_data:
                            vehicle_data['additional'] = {}
                        vehicle_data['additional']['total_keepers'] = int(keepers_match.group(1))
                        logger.info(f"Extracted total keepers from text: {keepers_match.group(1)}")
                except Exception as e2:
                    logger.debug(f"Text-based total keepers extraction failed: {e2}")
            
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Error extracting vehicle data: {e}")
            return None
    
    def _extract_basic_info(self, driver):
        """Extract basic vehicle information like make, model"""
        basic_info = {}
        
        try:
            # Get page source for pattern matching
            page_source = driver.page_source
            
            # Extract vehicle title/heading
            title_selectors = [
                "h1", "h2", ".vehicle-title", ".car-title", 
                ".main-title", ".vehicle-name"
            ]
            
            for selector in title_selectors:
                try:
                    title_element = driver.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_element.text.strip()
                    if title_text and len(title_text) > 3:
                        basic_info['title'] = title_text
                        break
                except NoSuchElementException:
                    continue
            
            # Extract make and model using comprehensive patterns
            self._extract_make_model(page_source, basic_info)
            
            # Extract vehicle image if available
            try:
                img_element = driver.find_element(By.CSS_SELECTOR, "img[src*='vehicle'], img[alt*='vehicle'], img[src*='car']")
                basic_info['image_url'] = img_element.get_attribute('src')
            except NoSuchElementException:
                basic_info['image_url'] = 'https://www.checkcardetails.co.uk/images/account.png'
                
        except Exception as e:
            logger.error(f"Error extracting basic info: {e}")
            
        return basic_info
    
    def _extract_make_model(self, page_source, basic_info):
        """Extract make and model using comprehensive pattern matching"""
        try:
            # Mercedes-Benz models (CLA, A-Class, C-Class, etc.)
            mercedes_patterns = [
                (r'CLA\s*\d{3}', 'Mercedes-Benz', 'CLA'),
                (r'CLA.*CDi', 'Mercedes-Benz', 'CLA'),
                (r'CLA.*Sport', 'Mercedes-Benz', 'CLA'),
                (r'A\s*Class', 'Mercedes-Benz', 'A-Class'),
                (r'C\s*Class', 'Mercedes-Benz', 'C-Class'),
                (r'E\s*Class', 'Mercedes-Benz', 'E-Class'),
                (r'S\s*Class', 'Mercedes-Benz', 'S-Class'),
                (r'GLA\s*\d{3}', 'Mercedes-Benz', 'GLA'),
                (r'GLC\s*\d{3}', 'Mercedes-Benz', 'GLC'),
                (r'GLE\s*\d{3}', 'Mercedes-Benz', 'GLE'),
                (r'GLS\s*\d{3}', 'Mercedes-Benz', 'GLS')
            ]
            
            # Other luxury brands
            luxury_patterns = [
                (r'F12.*Berlinetta', 'Ferrari', 'F12 Berlinetta'),
                (r'F12berlinetta', 'Ferrari', 'F12 Berlinetta'),
                (r'F430', 'Ferrari', 'F430'),
                (r'458', 'Ferrari', '458'),
                (r'488', 'Ferrari', '488'),
                (r'Gallardo', 'Lamborghini', 'Gallardo'),
                (r'Huracan', 'Lamborghini', 'Huracan'),
                (r'Aventador', 'Lamborghini', 'Aventador'),
                (r'911', 'Porsche', '911'),
                (r'Cayenne', 'Porsche', 'Cayenne'),
                (r'Panamera', 'Porsche', 'Panamera')
            ]
            
            # Common brands
            common_patterns = [
                (r'Corsa', 'Vauxhall', 'Corsa'),
                (r'Astra', 'Vauxhall', 'Astra'),
                (r'Insignia', 'Vauxhall', 'Insignia'),
                (r'Focus', 'Ford', 'Focus'),
                (r'Fiesta', 'Ford', 'Fiesta'),
                (r'Golf', 'Volkswagen', 'Golf'),
                (r'A6', 'Audi', 'A6'),
                (r'A4', 'Audi', 'A4'),
                (r'A3', 'Audi', 'A3'),
                (r'3 Series', 'BMW', '3 Series'),
                (r'5 Series', 'BMW', '5 Series')
            ]
            
            # Combine all patterns
            all_patterns = mercedes_patterns + luxury_patterns + common_patterns
            
            # Check patterns in order of specificity
            for pattern, make, model in all_patterns:
                if re.search(pattern, page_source, re.IGNORECASE):
                    basic_info['make'] = make
                    basic_info['model'] = model
                    logger.info(f"Detected {make} {model} using pattern: {pattern}")
                    return
                    
            # Fallback: Set to Unknown if not detected
            basic_info['make'] = 'Unknown'
            basic_info['model'] = 'Unknown'
            
        except Exception as e:
            logger.error(f"Error extracting make/model: {e}")
            basic_info['make'] = 'Unknown'
            basic_info['model'] = 'Unknown'
    
    def _extract_tax_mot_info(self, driver):
        """Extract tax and MOT expiry information"""
        tax_mot = {}
        
        try:
            # Look for TAX information
            tax_patterns = [
                "//text()[contains(., 'TAX')]/following::text()[contains(., 'Expires:')]",
                "//*[contains(text(), 'TAX')]/following::*[contains(text(), 'Expires:')]",
                "//*[contains(text(), 'Tax')]/following::*[contains(text(), 'expires')]"
            ]
            
            for pattern in tax_patterns:
                try:
                    elements = driver.find_elements(By.XPATH, pattern)
                    for element in elements:
                        text = element.text if hasattr(element, 'text') else str(element)
                        if 'expires' in text.lower():
                            tax_mot['tax_expiry'] = self._clean_date_text(text)
                            break
                    if 'tax_expiry' in tax_mot:
                        break
                except:
                    continue
            
            # Look for MOT information
            mot_patterns = [
                "//text()[contains(., 'MOT')]/following::text()[contains(., 'Expires:')]",
                "//*[contains(text(), 'MOT')]/following::*[contains(text(), 'Expires:')]",
                "//*[contains(text(), 'Mot')]/following::*[contains(text(), 'expires')]"
            ]
            
            for pattern in mot_patterns:
                try:
                    elements = driver.find_elements(By.XPATH, pattern)
                    for element in elements:
                        text = element.text if hasattr(element, 'text') else str(element)
                        if 'expires' in text.lower():
                            tax_mot['mot_expiry'] = self._clean_date_text(text)
                            break
                    if 'mot_expiry' in tax_mot:
                        break
                except:
                    continue
            
            # Look for days left information
            days_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'days left')]")
            for element in days_elements:
                text = element.text
                if 'days left' in text:
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        # Try to determine if it's tax or MOT based on context
                        parent_text = element.find_element(By.XPATH, "..").text.lower()
                        if 'tax' in parent_text:
                            tax_mot['tax_days_left'] = numbers[0]
                        elif 'mot' in parent_text:
                            tax_mot['mot_days_left'] = numbers[0]
                            
        except Exception as e:
            logger.error(f"Error extracting tax/MOT info: {e}")
            
        return tax_mot
    
    def _extract_vehicle_details(self, driver):
        """Extract vehicle details from table format"""
        details = {}
        
        try:
            # Look for table with vehicle details
            table_selectors = [
                "table", ".vehicle-details table", ".car-details table",
                ".details-table", ".vehicle-info-table"
            ]
            
            for selector in table_selectors:
                try:
                    table = driver.find_element(By.CSS_SELECTOR, selector)
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            key = cells[0].text.strip()
                            value = cells[1].text.strip()
                            if key and value:
                                details[self._normalize_key(key)] = value
                                
                    if details:  # If we found data, break
                        break
                        
                except NoSuchElementException:
                    continue
            
            # Also look for definition lists or other formats
            if not details:
                dl_elements = driver.find_elements(By.TAG_NAME, "dl")
                for dl in dl_elements:
                    dt_elements = dl.find_elements(By.TAG_NAME, "dt")
                    dd_elements = dl.find_elements(By.TAG_NAME, "dd")
                    
                    for dt, dd in zip(dt_elements, dd_elements):
                        key = dt.text.strip()
                        value = dd.text.strip()
                        if key and value:
                            details[self._normalize_key(key)] = value
                            
        except Exception as e:
            logger.error(f"Error extracting vehicle details: {e}")
            
        return details
    
    def _extract_mileage_info(self, driver):
        """Extract mileage information with advanced rollback detection"""
        mileage = {}
        
        try:
            # Look for mileage section
            mileage_keywords = ['mileage', 'last mot mileage', 'average', 'status']
            
            for keyword in mileage_keywords:
                try:
                    element = driver.find_element(By.XPATH, f"//*[contains(text(), '{keyword}')]/following::*[1]")
                    value = element.text.strip()
                    if value:
                        mileage[self._normalize_key(keyword)] = value
                except NoSuchElementException:
                    continue
            
            # Enhanced mileage history extraction with rollback detection
            mileage_data = []
            suspicious_patterns = []
            
            # Look for mileage history table
            try:
                tables = driver.find_elements(By.CSS_SELECTOR, "table")
                for table in tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
                            date_text = cells[0].text.strip()
                            mileage_text = cells[2].text.strip() if len(cells) > 2 else cells[1].text.strip()
                            
                            # Extract date and mileage
                            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_text)
                            mileage_match = re.search(r'(\d+)', mileage_text.replace(',', ''))
                            
                            if date_match and mileage_match:
                                mileage_data.append({
                                    'date': date_match.group(1),
                                    'mileage': int(mileage_match.group(1)),
                                    'original_text': mileage_text
                                })
                
                # Analyze for rollbacks (like the 51,411 mile reduction shown in your image)
                if len(mileage_data) > 1:
                    # Sort by date (oldest first for proper chronological analysis)
                    from datetime import datetime
                    mileage_data.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y'))
                    
                    rollbacks = []
                    for i in range(1, len(mileage_data)):
                        current_mileage = mileage_data[i]['mileage']
                        previous_mileage = mileage_data[i-1]['mileage']
                        
                        if current_mileage < previous_mileage:
                            rollback_amount = previous_mileage - current_mileage
                            rollback_info = {
                                'from_date': mileage_data[i-1]['date'],
                                'to_date': mileage_data[i]['date'],
                                'from_mileage': previous_mileage,
                                'to_mileage': current_mileage,
                                'rollback_amount': rollback_amount,
                                'severity': 'CRITICAL' if rollback_amount > 30000 else 'HIGH' if rollback_amount > 10000 else 'MEDIUM'
                            }
                            rollbacks.append(rollback_info)
                            
                            if rollback_amount > 30000:  # Major rollbacks like the 51,411 shown
                                suspicious_patterns.append(f"CRITICAL ROLLBACK: {rollback_amount:,} miles reduced between {mileage_data[i-1]['date']} and {mileage_data[i]['date']}")
                                logger.error(f"MAJOR MILEAGE ROLLBACK DETECTED: {previous_mileage:,} -> {current_mileage:,} (-{rollback_amount:,} miles)")
                    
                    if rollbacks or suspicious_patterns:
                        mileage['analysis'] = {
                            'total_readings': len(mileage_data),
                            'odometer_issues': {
                                'has_issues': True,
                                'rollbacks': rollbacks,
                                'suspicious_patterns': suspicious_patterns,
                                'clocking_suspected': len([r for r in rollbacks if r['rollback_amount'] > 30000]) > 0
                            }
                        }
                        mileage['mileage_issues'] = "Yes"
                        logger.warning(f"Mileage analysis complete: {len(rollbacks)} rollbacks detected, {len(suspicious_patterns)} critical issues")
                    
            except Exception as e:
                logger.debug(f"Enhanced mileage analysis failed: {e}")
                    
        except Exception as e:
            logger.error(f"Error extracting mileage info: {e}")
            
        return mileage
    
    def _extract_performance_data(self, driver):
        """Extract performance data like power, torque, max speed"""
        performance = {}
        
        try:
            performance_keywords = ['power', 'max speed', 'torque', 'bhp', 'mph', 'ftlb']
            
            for keyword in performance_keywords:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                    for element in elements:
                        text = element.text
                        # Extract numbers and units
                        matches = re.findall(r'(\d+(?:\.\d+)?)\s*([A-Za-z%]+)', text)
                        if matches:
                            value, unit = matches[0]
                            performance[self._normalize_key(keyword)] = f"{value} {unit}"
                            break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting performance data: {e}")
            
        return performance
    
    def _extract_fuel_economy(self, driver):
        """Extract fuel economy information"""
        fuel_economy = {}
        
        try:
            economy_keywords = ['urban', 'extra urban', 'combined', 'mpg']
            
            for keyword in economy_keywords:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                    for element in elements:
                        text = element.text
                        # Look for MPG values
                        mpg_match = re.search(r'(\d+(?:\.\d+)?)\s*MPG', text, re.IGNORECASE)
                        if mpg_match:
                            fuel_economy[self._normalize_key(keyword)] = f"{mpg_match.group(1)} MPG"
                            break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting fuel economy: {e}")
            
        return fuel_economy
    
    def _extract_safety_ratings(self, driver):
        """Extract safety ratings"""
        safety = {}
        
        try:
            safety_keywords = ['child', 'adult', 'pedestrian', 'safety']
            
            for keyword in safety_keywords:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                    for element in elements:
                        text = element.text
                        # Look for percentage values
                        percent_match = re.search(r'(\d+)\s*%', text)
                        if percent_match:
                            safety[self._normalize_key(keyword)] = f"{percent_match.group(1)}%"
                            break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting safety ratings: {e}")
            
        return safety
    
    def _extract_additional_info(self, driver):
        """Extract additional information like CO2 emissions, tax costs, etc."""
        additional = {}
        
        try:
            # CO2 emissions
            try:
                co2_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'CO2') or contains(text(), 'g/km')]")
                for element in co2_elements:
                    text = element.text
                    co2_match = re.search(r'(\d+)\s*g/km', text)
                    if co2_match:
                        additional['co2_emissions'] = f"{co2_match.group(1)} g/km"
                        break
            except:
                pass
            
            # Tax costs - enhanced extraction
            try:
                # Multiple strategies for tax cost extraction
                page_text = driver.page_source.lower()
                
                # Strategy 1: Direct element search
                tax_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '£') and contains(text(), 'months')]")
                for element in tax_elements:
                    text = element.text
                    if '12 months' in text.lower():
                        price_match = re.search(r'£(\d+(?:\.\d{2})?)', text)
                        if price_match:
                            additional['tax_12_months'] = f"£{price_match.group(1)}"
                    elif '6 months' in text.lower():
                        price_match = re.search(r'£(\d+(?:\.\d{2})?)', text)
                        if price_match:
                            additional['tax_6_months'] = f"£{price_match.group(1)}"
                
                # Strategy 2: Page text pattern matching for tax costs
                if not additional.get('tax_12_months'):
                    tax_12_match = re.search(r'12\s*months?[:\s]*£(\d+(?:\.\d{2})?)', page_text, re.IGNORECASE)
                    if tax_12_match:
                        additional['tax_12_months'] = f"£{tax_12_match.group(1)}"
                
                if not additional.get('tax_6_months'):
                    tax_6_match = re.search(r'6\s*months?[:\s]*£(\d+(?:\.\d{2})?)', page_text, re.IGNORECASE)
                    if tax_6_match:
                        additional['tax_6_months'] = f"£{tax_6_match.group(1)}"
                
                # Strategy 3: Tax rate table extraction
                try:
                    tax_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'months') or contains(., 'Month')]")
                    for row in tax_rows:
                        row_text = row.text.lower()
                        if '12' in row_text and 'month' in row_text:
                            price_match = re.search(r'£(\d+(?:\.\d{2})?)', row.text)
                            if price_match and not additional.get('tax_12_months'):
                                additional['tax_12_months'] = f"£{price_match.group(1)}"
                        elif '6' in row_text and 'month' in row_text:
                            price_match = re.search(r'£(\d+(?:\.\d{2})?)', row.text)
                            if price_match and not additional.get('tax_6_months'):
                                additional['tax_6_months'] = f"£{price_match.group(1)}"
                except:
                    pass
                    
                # Extract V5C Certificate Count
                v5c_count_match = re.search(r'V5C Certificate Count[:\s]*(\d+)', page_text, re.IGNORECASE)
                if v5c_count_match:
                    additional['v5c_certificate_count'] = int(v5c_count_match.group(1))
                    logger.info(f"Extracted V5C certificate count: {v5c_count_match.group(1)}")
                    
                # Extract Export status
                exported_match = re.search(r'Exported[:\s]*(YES|NO)', page_text, re.IGNORECASE)
                if exported_match:
                    additional['exported'] = exported_match.group(1).upper()
                    logger.info(f"Extracted export status: {exported_match.group(1)}")
                    
                # Extract Outstanding Recall status
                recall_match = re.search(r'Has Outstanding Recall[:\s]*(YES|NO)', page_text, re.IGNORECASE)
                if recall_match:
                    additional['has_outstanding_recall'] = recall_match.group(1).upper()
                    logger.info(f"Extracted recall status: {recall_match.group(1)}")
                
                logger.info(f"Tax extraction results: 6-month: {additional.get('tax_6_months', 'Not found')}, 12-month: {additional.get('tax_12_months', 'Not found')}")
            except Exception as e:
                logger.warning(f"Tax cost extraction failed: {e}")
                
        except Exception as e:
            logger.error(f"Error extracting additional info: {e}")
            
        return additional
    
    def _normalize_key(self, key):
        """Normalize key names for consistent data structure"""
        return key.lower().replace(' ', '_').replace('/', '_').replace('-', '_')
    
    def _clean_date_text(self, text):
        """Clean and extract date from text"""
        # Look for date patterns
        date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', text)
        if date_match:
            return date_match.group(1)
        return text.strip()
