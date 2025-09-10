Bleach Soul Deck - Card Generation Utility
This utility generates card images for the "Bleach Soul Deck" game based on data from a card_data.json file.

Setup
Install Python: Make sure you have Python 3 installed on your system.

Install Libraries: This script requires the Pillow library for image manipulation and requests for downloading assets. You can install them using pip:

pip install Pillow requests

File Structure: Place the following files in the same directory:

card_generator.py (the main script)

card_data.json (the card data file)

How to Use
Edit Card Data: Open card_data.json to add, remove, or modify cards. You can change stats, text, and the artwork_url. Use any publicly accessible image URL for the artwork.

Run the Generator: Execute the script from your terminal:

python card_generator.py

Use the GUI: A small window will appear. Click the "Generate All Cards" button.

Check the Output: The script will download the necessary fonts (a one-time process) and artwork, then generate the card images. The final .png files will be saved in a new folder named generated_cards.

Notes
The script automatically creates the generated_cards and fonts directories if they don't exist.

An internet connection is required the first time you run the script to download the fonts and for every run to download the card artwork.

If you encounter any errors, check the console output for details. Common issues include malformed JSON in card_data.json or invalid image URLs.