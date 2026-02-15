import requests
import pandas as pd
import random

import json
import os

class DestinationLoader:
    def __init__(self):
        # Optimized URL with specific fields to reduce payload size and improve reliability
        self.fields = "name,cca2,region,subregion,population,capital,latlng"
        self.base_url = f"https://restcountries.com/v3.1/all?fields={self.fields}"
        self.numbeo_path = 'data/numbeo_data.csv'
        self.fallback_path = 'data/fallback_destinations.json'

    def fetch_data(self):
        countries_data = []
        
        # 1. Fetch Real Country Data (with Fallback)
        try:
            response = requests.get(self.base_url, timeout=5)
            response.raise_for_status()
            countries_data = response.json()
        except Exception as e:
            if os.path.exists(self.fallback_path):
                try:
                    with open(self.fallback_path, 'r', encoding='utf-8') as f:
                        countries_data = json.load(f)
                except:
                    return []
            else:
                return []

        # 2. Load Cost Data
        cost_df = pd.DataFrame()
        try:
            cost_df = pd.read_csv(self.numbeo_path)
        except:
            pass

        processed_destinations = []

        for country in countries_data:
            try:
                name = country['name']['common']
                region = country.get('region', 'Unknown')
                subregion = country.get('subregion', 'Unknown')
                
                # Map Americas to specific continents for our UI
                if region == 'Americas':
                    if 'North' in subregion or 'Central' in subregion or 'Caribbean' in subregion:
                        region = 'North America'
                    else:
                        region = 'South America'

                population = country.get('population', 0)
                # Capital is a list
                capital = country.get('capital', ['Unknown'])[0] if country.get('capital') else 'Unknown'
                
                # Skip non-destinations (e.g. Antarctica) or tiny islands for this demo if needed
                if population < 100000:
                    continue

                # Estimate Base Cost (Heuristic based on region + random variance for demo)
                base_cost = 100 # Default
                
                if region == 'Europe' or region == 'North America':
                    base_cost = 150
                elif region == 'Africa':
                    base_cost = 80
                elif region == 'Asia':
                    base_cost = 90
                elif region == 'Oceania':
                    base_cost = 140
                elif region == 'South America':
                    base_cost = 110
                
                # Refine with CSV if match found
                if not cost_df.empty:
                    match = cost_df[cost_df['Country'] == name]
                    if not match.empty:
                        # Normalize: NY is 100 index ~ $250/day
                        idx = match.iloc[0]['Cost of Living Index']
                        base_cost = (idx / 100) * 250
                    elif capital != 'Unknown':
                         match_city = cost_df[cost_df['City'] == capital]
                         if not match_city.empty:
                             idx = match_city.iloc[0]['Cost of Living Index']
                             base_cost = (idx / 100) * 250

                processed_destinations.append({
                    "city": capital,
                    "country": name,
                    "country_code": country.get('cca2', ''),
                    "continent": region,
                    "subregion": subregion,
                    "base_cost": int(base_cost),
                    "population": population,
                    "lat": country['latlng'][0] if country.get('latlng') else 0,
                    "lng": country['latlng'][1] if country.get('latlng') else 0,
                    # Construct a description for TF-IDF
                    "description": f"A beautiful destination in {subregion}, {region}. Known for its culture and population of {population:,}. Capital city is {capital}."
                })
            except Exception as e:
                continue
                
        return processed_destinations
