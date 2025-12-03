"""Configuration settings for the price scraper project."""

import os

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

# List of products to track
PRODUCTS_FILE = BASE_PATH + "//" + "products.csv"
