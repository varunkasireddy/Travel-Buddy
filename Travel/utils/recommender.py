import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from .api_clients import WeatherClient, SafetyClient, CurrencyClient
from .destinations_data import DestinationLoader
from .ml_models import HybridMLEngine

class TravelRecommender:
    def __init__(self):
        self.weather_client = WeatherClient()
        self.safety_client = SafetyClient()
        self.currency_client = CurrencyClient()
        self.loader = DestinationLoader()
        self.ml_engine = HybridMLEngine()
        
        # Load and Cache Data
        self.destinations_data = self.loader.fetch_data()
        self.df = pd.DataFrame(self.destinations_data)
        
        # Initialize ML Models
        self._train_models()

    def _train_models(self):
        if self.df.empty:
            return

        # 1. Text Features (TF-IDF on Description/Region)
        # This helps match "vibe" (e.g., specific subregions)
        self.tfidf = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.tfidf.fit_transform(self.df['description'])

        # 2. Numerical Features (Cost, Population)
        self.scaler = MinMaxScaler()
        # Normalize cost and population
        self.num_features = self.scaler.fit_transform(self.df[['base_cost', 'population']])

        # 3. Combine Features
        # Stack numerical and text features
        # Note: TF-IDF is sparse, so we convert to array for simple concatenation 
        # (okay for <300 countries)
        self.features = np.hstack([self.num_features, self.tfidf_matrix.toarray()])

        # 4. Nearest Neighbors Model
        self.nn_model = NearestNeighbors(n_neighbors=10, metric='cosine')
        self.nn_model.fit(self.features)

    def _resolve_origin_coords(self, city):
        if not self.df.empty:
            match = self.df[self.df['city'].str.lower() == city.lower()]
            if not match.empty:
                return match.iloc[0]['lat'], match.iloc[0]['lng']
        return 51.5, -0.12

    def recommend(self, continent, budget, days, people, currency='USD', origin_city='London'):
        if self.df.empty:
            return {"recommendations": [], "analysis": {"error": "No data available"}}

        # 0. Handle Currency Conversion
        rates = self.currency_client.get_rates()
        budget_usd = float(budget)
        if currency != 'USD' and currency in rates:
            budget_usd = float(budget) / rates[currency]
        
        # Resolve Origin
        origin_lat, origin_lng = self._resolve_origin_coords(origin_city)
        
        # 1. Filter and Score Candidates
        candidates = []
        eligible_df = self.df[self.df['continent'] == continent].copy()
        
        if eligible_df.empty:
            eligible_df = self.df.copy()
            continent_msg = f"No data for {continent}, searching globally."
        else:
            continent_msg = None

        min_cost_found = float('inf')
        rejected_count = 0

        for index, row in eligible_df.iterrows():
            # A. Safety Score
            safety_score = self.safety_client.get_safety_score(row['country_code'])
            
            # B. Daily Cost (Hybrid)
            ml_daily = self.ml_engine.predict_daily_cost(row['continent'], row['population'], safety_score)
            final_daily_cost = (row['base_cost'] * 0.7) + (ml_daily * 0.3)
            
            # C. Flight Cost (ML Prediction)
            ml_flight_cost = self.ml_engine.predict_flight_cost(
                origin_lat, origin_lng, row['lat'], row['lng'], row['continent']
            )
            
            # D. Total Trip Cost
            total_trip_cost = (final_daily_cost * days * people) + (ml_flight_cost * people)
            
            if total_trip_cost < min_cost_found:
                min_cost_found = total_trip_cost

            # Budget Check
            if total_trip_cost > budget_usd:
                rejected_count += 1
                continue

            # Fetch Weather
            weather_data = self.weather_client.get_weather(row['city'])
            
            candidates.append({
                "city": row['city'],
                "country": row['country'],
                "country_code": row['country_code'],
                "lat": row['lat'],
                "lng": row['lng'],
                "estimated_cost": int(total_trip_cost * (rates.get(currency, 1) if currency != 'USD' else 1)),
                "flight_cost_est": int(ml_flight_cost),
                "currency": currency,
                "safety_raw": safety_score,
                "safety_score": round(safety_score, 1),
                "description": row['description'],
                "weather": f"{weather_data['temp']}°C, {weather_data['description']}" if weather_data['temp'] != "N/A" else "Unknown",
                "weather_temp": weather_data['temp'] if weather_data['temp'] != "N/A" else 20,
                "total_cost_usd": total_trip_cost
            })

        if not candidates:
             return {
                "recommendations": [], 
                "analysis": {
                    "rejected_budget": rejected_count,
                    "min_cost_found": int(min_cost_found * (rates.get(currency, 1) if currency != 'USD' else 1)) if min_cost_found != float('inf') else 0,
                    "user_budget": budget,
                    "currency": currency,
                    "continent_message": continent_msg
                }
            }

        # 2. ML Ranking
        for c in candidates:
            # Distance from ideal budget (0 is best)
            cost_score = min(1, c['total_cost_usd'] / budget_usd)
            
            # Safety (0 is best in raw)
            safe_score = c['safety_raw'] / 5.0
            
            # Weather (25 is ideal)
            weather_diff = abs(float(c['weather_temp']) - 25) / 20.0
            
            # Composite Score (Lower is better)
            raw_score = (cost_score * 0.5) + (safe_score * 0.3) + (weather_diff * 0.2)
            c['ml_score'] = round(max(0, (1 - raw_score) * 100), 1)

        candidates.sort(key=lambda x: x['ml_score'], reverse=True)
        
        return {
            "recommendations": candidates[:4],
            "analysis": {
                "total_checked": len(eligible_df),
                "rejected_budget": rejected_count,
                "min_cost_found": 0,
                "continent_message": continent_msg,
                "user_budget": budget,
                "currency": currency
            }
        }
