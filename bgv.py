from flask import Flask, jsonify, request
import requests
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import tempfile
import os

app = Flask(__name__)

def convert_to_usda_format(nutrition_data):
    """Converts nutrition data to USDA format."""
    usda_data = {
        "energy_kcal": nutrition_data["nutriments"].get("energy-kcal_100g", 0),
        "protein_g": nutrition_data["nutriments"].get("proteins_100g", 0),
        "fat_g": nutrition_data["nutriments"].get("fat_100g", 0),
        "carbohydrate_g": nutrition_data["nutriments"].get("carbohydrates_100g", 0),
        "sugars_g": nutrition_data["nutriments"].get("sugars_100g", 0),
        "fiber_g": 0,
        "calcium_mg": 0,
        "iron_mg": 0,
        "sodium_mg": nutrition_data["nutriments"].get("sodium_100g", 0) * 1000,
        "saturated_fat_g": nutrition_data["nutriments"].get("saturated-fat_100g", 0),
        "trans_fat_g": nutrition_data["nutriments"].get("trans-fat_100g", 0),
        "added_sugars_g": nutrition_data["nutriments"].get("added-sugars_100g", 0),
        "cholesterol_mg": 0,
    }
    return usda_data

@app.route('/nutrition/usda/<product_code>')
def get_usda_nutrition(product_code):
    """Fetches nutrition data, converts it to USDA format."""
    url = f"https://world.openfoodfacts.org/api/v3/product/{product_code}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data["status"] == "success" and "product" in data and "nutriments" in data["product"]: #Corrected status check.
            usda_nutrition = convert_to_usda_format(data["product"])
            return jsonify(usda_nutrition), 200
        else:
            return jsonify({"error": "Nutrition data not found for this product."}), 404

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to fetch data: {e}"}), 500
    except KeyError:
        return jsonify({"error": "Product data format is incorrect or nutriments are missing."}), 500

def extract_barcode_from_image(file_path):
    """Extracts barcode data from an image file."""
    try:
        img = cv2.imread(file_path)
        if img is None:
            return None, "Error: Could not open or find the image."
        decoded_objects = decode(img)
        if not decoded_objects:
            return None, "No barcode found in the image..........."
        return decoded_objects, None
    except Exception as e:
        return None, f"An error occurred: {e}"

@app.route('/barcode', methods=['POST'])
def barcode_reader():
    """API endpoint to read barcode and return USDA formatted nutrition data."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file uploaded'}), 400
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if image_file:
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_image:
                image_file.save(temp_image.name)
                temp_file_path = temp_image.name
            decoded_data, error_message = extract_barcode_from_image(temp_file_path)
            os.unlink(temp_file_path)
            if error_message:
                return jsonify({'error': error_message}), 400
            if decoded_data:
                barcode_texts = []
                for obj in decoded_data:
                    barcode_texts.append(obj.data.decode('utf-8'))
                if len(barcode_texts) == 1:
                    print(barcode_texts[0])
                    return get_usda_nutrition(barcode_texts[0])
                else:
                    nutrition_list = []
                    for barcode in barcode_texts:
                        nutrition_list.append(get_usda_nutrition(barcode).get_json())
                    return jsonify(nutrition_list)
            else:
                return jsonify({'error': 'No barcode found'}), 404
        except Exception as e:
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file'}), 400

if __name__ == '__main__':
    app.run(debug=True)