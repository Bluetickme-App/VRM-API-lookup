#!/usr/bin/env python3
"""
Test script for OCR functionality
Creates a simple test image with text and tests the OCR processor
"""

import os
from PIL import Image, ImageDraw, ImageFont
from ocr_processor import NumberPlateOCR
import tempfile

def create_test_number_plate(registration="AB12 CDE"):
    """Create a simple test number plate image"""
    # Create image
    width, height = 400, 100
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a basic font
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 36)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = None
    
    # Draw black border (UK plate style)
    draw.rectangle([10, 10, width-10, height-10], outline='black', width=3)
    
    # Draw registration text
    text = registration
    if font:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width, text_height = 100, 20  # fallback
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), text, fill='black', font=font)
    
    return img

def test_ocr_functionality():
    """Test the OCR processor"""
    print("Testing OCR functionality...")
    
    # Initialize OCR processor
    ocr = NumberPlateOCR()
    
    # Test registrations
    test_plates = ["AB12 CDE", "X123 ABC", "DA07BWF", "RE13CEO"]
    
    for plate in test_plates:
        print(f"\nTesting with plate: {plate}")
        
        # Create test image
        img = create_test_number_plate(plate)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file.name, 'PNG')
            
            # Test OCR
            result = ocr.process_image(tmp_file.name, is_base64=False)
            
            print(f"OCR Result: {result}")
            
            if result.get('best_match'):
                print(f"✅ Detected: {result['best_match']}")
                if result['best_match'].replace(' ', '') == plate.replace(' ', ''):
                    print("✅ Perfect match!")
                else:
                    print(f"⚠️ Close match (expected: {plate})")
            else:
                print(f"❌ No plate detected")
                if result.get('extracted_text'):
                    print(f"Raw text: '{result['extracted_text']}'")
            
            # Clean up
            os.unlink(tmp_file.name)

if __name__ == "__main__":
    test_ocr_functionality()