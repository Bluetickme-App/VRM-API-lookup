"""
OCR Number Plate Recognition System
Extracts vehicle registration numbers from uploaded images
"""

import re
from PIL import Image
import logging
import base64
import io
import numpy as np
import os
from openai import OpenAI

# Try to import OpenCV with fallback
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available - using PIL-only processing")

# Try to import Tesseract with fallback  
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    TESSERACT_AVAILABLE = False
    logging.warning("Tesseract not available - OCR functionality limited")

# Initialize OpenAI client for enhanced OCR
openai_client = None
try:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
        logging.info("OpenAI Vision API available for enhanced OCR")
    else:
        OPENAI_AVAILABLE = False
        openai_client = None
        logging.warning("OPENAI_API_KEY not found - OpenAI vision not available")
except Exception as e:
    OPENAI_AVAILABLE = False
    openai_client = None
    logging.warning(f"OpenAI initialization failed: {e}")

logger = logging.getLogger(__name__)

class NumberPlateOCR:
    """OCR processor for UK number plate recognition"""
    
    def __init__(self):
        # UK number plate patterns
        self.uk_patterns = [
            r'[A-Z]{2}[0-9]{2}\s?[A-Z]{3}',  # Standard format: AB12 CDE
            r'[A-Z][0-9]{1,3}\s?[A-Z]{3}',   # Older format: A123 BCD
            r'[A-Z]{3}\s?[0-9]{1,3}[A-Z]',   # Older format: ABC 123D
            r'[0-9]{1,4}\s?[A-Z]{1,3}',      # Very old format: 1234 AB
        ]
    
    def process_image(self, image_data, is_base64=True):
        """Enhanced processing for real-world number plate images"""
        try:
            if not TESSERACT_AVAILABLE:
                return {'error': 'OCR functionality not available - Tesseract not installed'}
            
            # Convert image data to PIL format
            if is_base64:
                image = self._decode_base64_image(image_data)
            else:
                try:
                    image = Image.open(image_data)
                except Exception as e:
                    logger.error(f"Failed to open image file: {e}")
                    return {'error': 'Invalid image file format'}
            
            if image is None:
                return {'error': 'Failed to load image'}
            
            # Convert to RGB if needed
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Try multiple processing strategies
            all_plates = []
            all_extracted_text = []
            
            # Strategy 1: Original preprocessing
            processed_image = self._preprocess_image(image)
            extracted_text = self._extract_text(processed_image)
            all_extracted_text.append(f"Strategy1: '{extracted_text}'")
            plates = self._find_number_plates(extracted_text)
            all_plates.extend(plates)
            
            # Strategy 2: Try with original image (no preprocessing)
            original_text = self._extract_text(image)
            all_extracted_text.append(f"Original: '{original_text}'")
            original_plates = self._find_number_plates(original_text)
            all_plates.extend(original_plates)
            
            # Strategy 3: Try alternative OCR configs on processed image
            alt_plates = self._try_alternative_ocr(processed_image)
            all_plates.extend(alt_plates)
            
            # Strategy 4: Focus on yellow plate area (UK plates are often yellow)
            try:
                yellow_focused = self._extract_yellow_regions(image)
                if yellow_focused:
                    yellow_text = self._extract_text(yellow_focused)
                    all_extracted_text.append(f"Yellow: '{yellow_text}'")
                    yellow_plates = self._find_number_plates(yellow_text)
                    all_plates.extend(yellow_plates)
            except:
                pass
            
            # Strategy 5: OpenAI Vision API (when traditional OCR fails)
            if not all_plates and OPENAI_AVAILABLE:
                try:
                    openai_result = self._openai_vision_ocr(image_data if is_base64 else image)
                    if openai_result:
                        all_extracted_text.append(f"OpenAI: '{openai_result}'")
                        openai_plates = self._find_number_plates(openai_result)
                        all_plates.extend(openai_plates)
                        logger.info("OpenAI Vision API provided OCR result")
                except Exception as e:
                    logger.warning(f"OpenAI Vision OCR failed: {e}")
            
            # Remove duplicates and score by pattern matching
            unique_plates = list(set(all_plates))
            scored_plates = self._score_plate_candidates(unique_plates)
            
            debug_info = " | ".join(all_extracted_text) if not scored_plates else None
            
            return {
                'success': True,
                'extracted_text': " | ".join(all_extracted_text),
                'potential_plates': scored_plates,
                'best_match': scored_plates[0] if scored_plates else None,
                'debug_info': debug_info
            }
            
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return {'error': f'OCR processing failed: {str(e)}'}
    
    def _decode_base64_image(self, base64_data):
        """Decode base64 image data to PIL format"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(base64_data)
            
            # Convert to PIL Image
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            return pil_image
        except Exception as e:
            logger.error(f"Base64 decode error: {e}")
            return None
    
    def _preprocess_image(self, image):
        """Enhanced preprocessing for real-world number plate images"""
        try:
            # Convert to RGB first if needed
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Convert to numpy array for processing
            if image.mode == 'RGB':
                img_array = np.array(image)
                # Convert to grayscale with weighted average (better than simple convert)
                img_array = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
            else:
                img_array = np.array(image)
            
            img_array = img_array.astype(np.uint8)
            
            # Multiple enhancement strategies
            enhanced_images = []
            
            # Strategy 1: Basic contrast enhancement
            p5, p95 = np.percentile(img_array, (5, 95))
            if p95 > p5:
                contrast_enhanced = np.clip((img_array - p5) * 255 / (p95 - p5), 0, 255).astype(np.uint8)
                enhanced_images.append(Image.fromarray(contrast_enhanced))
            
            # Strategy 2: Adaptive thresholding for high contrast
            # Simple threshold at mean value
            mean_val = np.mean(img_array)
            binary = (img_array > mean_val * 1.1).astype(np.uint8) * 255
            enhanced_images.append(Image.fromarray(binary))
            
            # Strategy 3: Edge enhancement
            # Simple edge detection using differences
            try:
                # Use basic edge detection without scipy dependency
                pass
            except ImportError:
                # Fallback simple edge detection
                h, w = img_array.shape
                edges = np.zeros_like(img_array)
                for i in range(1, h-1):
                    for j in range(1, w-1):
                        gx = int(img_array[i-1,j-1]) - int(img_array[i-1,j+1]) + 2*(int(img_array[i,j-1]) - int(img_array[i,j+1])) + int(img_array[i+1,j-1]) - int(img_array[i+1,j+1])
                        gy = int(img_array[i-1,j-1]) - int(img_array[i+1,j-1]) + 2*(int(img_array[i-1,j]) - int(img_array[i+1,j])) + int(img_array[i-1,j+1]) - int(img_array[i+1,j+1])
                        edges[i,j] = min(255, abs(gx) + abs(gy))
                enhanced_images.append(Image.fromarray(edges.astype(np.uint8)))
            
            # Return the contrast enhanced version as primary (most reliable)
            return enhanced_images[0] if enhanced_images else Image.fromarray(img_array)
            
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            return image
    
    def _extract_text(self, image):
        """Extract text from preprocessed image using Tesseract"""
        try:
            if not TESSERACT_AVAILABLE:
                return ""
            
            # Configure Tesseract for better number plate recognition
            config = '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            
            # Extract text
            if TESSERACT_AVAILABLE:
                text = pytesseract.image_to_string(image, config=config)
            else:
                return ""
            
            # Clean up extracted text
            cleaned_text = re.sub(r'[^A-Z0-9\s]', '', text.upper())
            
            return cleaned_text.strip()
            
        except Exception as e:
            logger.error(f"Tesseract extraction error: {e}")
            return ""
    
    def _try_alternative_ocr(self, image):
        """Try alternative OCR configurations for better recognition"""
        try:
            if not TESSERACT_AVAILABLE:
                return []
            
            # Alternative configurations
            configs = [
                '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                '--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            ]
            
            for config in configs:
                try:
                    if TESSERACT_AVAILABLE:
                        text = pytesseract.image_to_string(image, config=config)
                    else:
                        continue
                    cleaned_text = re.sub(r'[^A-Z0-9\s]', '', text.upper()).strip()
                    if cleaned_text:
                        plates = self._find_number_plates(cleaned_text)
                        if plates:
                            return plates
                except:
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Alternative OCR error: {e}")
            return []
    
    def _find_number_plates(self, text):
        """Find potential UK number plates in extracted text"""
        plates = []
        
        # Remove excessive whitespace
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        # Try each pattern
        for pattern in self.uk_patterns:
            matches = re.findall(pattern, cleaned_text)
            for match in matches:
                # Clean up the match
                clean_match = re.sub(r'\s+', '', match)
                if len(clean_match) >= 4:  # Minimum realistic plate length
                    # Validate the format more strictly
                    if self.validate_uk_plate(clean_match):
                        plates.append(clean_match)
        
        # Remove duplicates and sort by length (longer matches are often better)
        unique_plates = list(set(plates))
        unique_plates.sort(key=len, reverse=True)
        
        # Filter out substrings of longer matches
        filtered_plates = []
        for plate in unique_plates:
            is_substring = False
            for other_plate in unique_plates:
                if plate != other_plate and plate in other_plate:
                    is_substring = True
                    break
            if not is_substring:
                filtered_plates.append(plate)
        
        return filtered_plates
    
    def validate_uk_plate(self, plate_text):
        """Validate if text looks like a valid UK plate"""
        if not plate_text or len(plate_text) < 4:
            return False
        
        # Check against UK patterns
        for pattern in self.uk_patterns:
            if re.match(pattern, plate_text.replace(' ', '')):
                return True
        
        return False
    
    def _extract_yellow_regions(self, image):
        """Extract yellow regions that might contain UK number plates"""
        try:
            # Convert to HSV for better yellow detection
            img_array = np.array(image)
            
            # Simple yellow detection in RGB
            # Yellow plates typically have high R and G, low B
            r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
            
            # Detect yellow-ish regions
            yellow_mask = (r > 150) & (g > 150) & (b < 100)
            
            if np.any(yellow_mask):
                # Create enhanced image focusing on yellow regions
                enhanced = img_array.copy()
                enhanced[~yellow_mask] = enhanced[~yellow_mask] * 0.3  # Darken non-yellow areas
                return Image.fromarray(enhanced.astype(np.uint8))
                
        except Exception as e:
            logger.error(f"Yellow region extraction error: {e}")
        
        return None
    
    def _score_plate_candidates(self, plates):
        """Score and sort plate candidates by likelihood"""
        if not plates:
            return []
        
        scored = []
        for plate in plates:
            score = 0
            clean_plate = plate.replace(' ', '')
            
            # Length scoring (UK plates are typically 7 characters)
            if len(clean_plate) == 7:
                score += 10
            elif 6 <= len(clean_plate) <= 8:
                score += 5
            
            # Pattern scoring for UK formats
            if re.match(r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$', clean_plate):
                score += 15  # Current format
            elif re.match(r'^[A-Z][0-9]{3}[A-Z]{3}$', clean_plate):
                score += 12  # Older format
            elif re.match(r'^[A-Z]{3}[0-9]{1,3}[A-Z]$', clean_plate):
                score += 10  # Even older format
            
            # Character quality scoring
            # Penalize ambiguous characters that might be OCR errors
            ambiguous_chars = clean_plate.count('0') + clean_plate.count('O') + clean_plate.count('I') + clean_plate.count('1')
            if ambiguous_chars < len(clean_plate) * 0.5:  # Less than half ambiguous
                score += 5
            
            scored.append((score, plate))
        
        # Sort by score (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)
        return [plate for score, plate in scored]
    
    def _openai_vision_ocr(self, image_data):
        """Use OpenAI Vision API to extract number plate text"""
        try:
            if not OPENAI_AVAILABLE or not openai_client:
                return None
                
            # Prepare image data for OpenAI
            if isinstance(image_data, str):
                # Already base64 encoded
                if image_data.startswith('data:image'):
                    image_url = image_data
                else:
                    image_url = f"data:image/jpeg;base64,{image_data}"
            else:
                # PIL Image - convert to base64
                buffer = io.BytesIO()
                image_data.save(buffer, format='JPEG')
                buffer.seek(0)
                img_base64 = base64.b64encode(buffer.getvalue()).decode()
                image_url = f"data:image/jpeg;base64,{img_base64}"
            
            # Call OpenAI Vision API with specialized prompt for UK number plates
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at reading UK vehicle number plates. Focus only on identifying the registration number visible on the number plate in the image. UK plates follow formats like 'AB12 CDE' (current), 'A123 BCD' (older), or 'ABC 123D' (older). Return only the registration number, nothing else."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What is the UK vehicle registration number visible on the number plate in this image? Return only the registration number (e.g., 'AB12 CDE'), nothing else."
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=50,
                temperature=0.1  # Low temperature for consistent results
            )
            
            if response.choices and response.choices[0].message.content:
                result = response.choices[0].message.content.strip()
                # Clean up the result - remove any extra text
                result = re.sub(r'[^A-Z0-9\s]', '', result.upper())
                logger.info(f"OpenAI Vision OCR result: '{result}'")
                return result
                
        except Exception as e:
            logger.error(f"OpenAI Vision OCR error: {e}")
            
        return None