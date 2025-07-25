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
    TESSERACT_AVAILABLE = False
    logging.warning("Tesseract not available - OCR functionality limited")

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
        """Process image and extract number plate text"""
        try:
            if not TESSERACT_AVAILABLE:
                return {'error': 'OCR functionality not available - Tesseract not installed'}
            
            # Convert image data to PIL format
            if is_base64:
                image = self._decode_base64_image(image_data)
            else:
                image = Image.open(image_data)
            
            if image is None:
                return {'error': 'Failed to load image'}
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Extract text using OCR
            extracted_text = self._extract_text(processed_image)
            
            # Find potential number plates
            plates = self._find_number_plates(extracted_text)
            
            return {
                'success': True,
                'extracted_text': extracted_text,
                'potential_plates': plates,
                'best_match': plates[0] if plates else None
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
        """Preprocess image for better OCR accuracy using PIL"""
        try:
            # Convert to grayscale if not already
            if image.mode != 'L':
                image = image.convert('L')
            
            # Convert to numpy array for processing
            img_array = np.array(image)
            
            # Simple contrast enhancement
            # Find the 5th and 95th percentiles
            p5, p95 = np.percentile(img_array, (5, 95))
            
            # Scale the image to use the full range
            img_array = np.clip((img_array - p5) * 255 / (p95 - p5), 0, 255).astype(np.uint8)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(img_array)
            
            return processed_image
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            return image  # Return original image if preprocessing fails
    
    def _extract_text(self, image):
        """Extract text from preprocessed image using Tesseract"""
        try:
            # Configure Tesseract for better number plate recognition
            config = '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            
            # Extract text
            text = pytesseract.image_to_string(image, config=config)
            
            # Clean up extracted text
            cleaned_text = re.sub(r'[^A-Z0-9\s]', '', text.upper())
            
            return cleaned_text.strip()
            
        except Exception as e:
            logger.error(f"Tesseract extraction error: {e}")
            return ""
    
    def _find_number_plates(self, text):
        """Find potential UK number plates in extracted text"""
        plates = []
        
        # Remove excessive whitespace
        cleaned_text = re.sub(r'\s+', ' ', text)
        
        # Try each pattern
        for pattern in self.uk_patterns:
            matches = re.findall(pattern, cleaned_text)
            for match in matches:
                # Clean up the match
                clean_match = re.sub(r'\s+', '', match)
                if len(clean_match) >= 4:  # Minimum realistic plate length
                    plates.append(clean_match)
        
        # Remove duplicates and sort by length (longer matches are often better)
        unique_plates = list(set(plates))
        unique_plates.sort(key=len, reverse=True)
        
        return unique_plates
    
    def validate_uk_plate(self, plate_text):
        """Validate if text looks like a valid UK plate"""
        if not plate_text or len(plate_text) < 4:
            return False
        
        # Check against UK patterns
        for pattern in self.uk_patterns:
            if re.match(pattern, plate_text.replace(' ', '')):
                return True
        
        return False