import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
import math
import warnings
import urllib3

# Suppress Warnings
warnings.filterwarnings("ignore", category=UserWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HybridMLEngine:
    def __init__(self):
        self.rf_flight_model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.lr_cost_model = LinearRegression()
        self.region_encoder = LabelEncoder()
        
        # Define feature names for consistent prediction
        self.flight_features = ['dist', 'region', 'peak']
        self.cost_features = ['region', 'pop', 'safety']
        
        # We need to train on initialization
        self._train_models()

    def _train_models(self):
        # ... (rest of the method stays same)
        regions = ['Europe', 'Asia', 'Americas', 'Africa', 'Oceania']
        self.region_encoder.fit(regions)
        
        flight_data = []
        for _ in range(500):
            dist = np.random.randint(200, 15000)
            region = np.random.choice(regions)
            region_code = self.region_encoder.transform([region])[0]
            is_peak = np.random.choice([0, 1])
            
            # Synthetic Formula: Base + (0.1 * dist) + Peak_Multiplier + Region_Variance
            price = 50 + (0.08 * dist) + (100 * is_peak) 
            if region == 'Oceania': price += 200
            if region == 'Africa': price += 150
            
            # Add noise
            price += np.random.normal(0, 50)
            
            flight_data.append([dist, region_code, is_peak, price])
            
        df_flight = pd.DataFrame(flight_data, columns=self.flight_features + ['price'])
        self.rf_flight_model.fit(df_flight[self.flight_features], df_flight['price'])

        # --- 2. Synthesize Data for Daily Costs (Linear Regression) ---
        cost_data = []
        for _ in range(500):
            region = np.random.choice(regions)
            region_code = self.region_encoder.transform([region])[0]
            pop_scale = np.random.randint(1, 100) # 1m to 100m equivalent
            safety = np.random.uniform(0, 5) # 0 is safe, 5 is unsafe
            
            # Formula: Base + Region + Pop - Safety_Penalty
            base = 50
            if region == 'Europe': base = 120
            if region == 'Americas': base = 100
            if region == 'Asia': base = 60
            
            cost = base + (0.5 * pop_scale) - (5 * safety)
            cost = max(20, cost) # Min floor
            
            cost_data.append([region_code, pop_scale, safety, cost])
            
        df_cost = pd.DataFrame(cost_data, columns=self.cost_features + ['cost'])
        self.lr_cost_model.fit(df_cost[self.cost_features], df_cost['cost'])

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371 # Earth radius in km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def predict_flight_cost(self, origin_lat, origin_lng, dest_lat, dest_lng, region):
        dist = self.haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        
        # Handle region encoding safely
        region_clean = region
        if region not in self.region_encoder.classes_:
            if 'America' in region: region_clean = 'Americas'
            else: region_clean = 'Europe' # Fallback
            
        region_code = self.region_encoder.transform([region_clean])[0]
        
        # Use DataFrame for prediction to avoid feature name warnings
        X = pd.DataFrame([[dist, region_code, 1]], columns=self.flight_features)
        prediction = self.rf_flight_model.predict(X)[0]
        return max(50, int(prediction))

    def predict_daily_cost(self, region, population, safety_score):
        region_clean = region
        if region not in self.region_encoder.classes_:
            if 'America' in region: region_clean = 'Americas'
            else: region_clean = 'Europe'
            
        region_code = self.region_encoder.transform([region_clean])[0]
        pop_scale = min(100, population / 1000000) # Scale down
        
        # Use DataFrame for prediction to avoid feature name warnings
        X = pd.DataFrame([[region_code, pop_scale, safety_score]], columns=self.cost_features)
        prediction = self.lr_cost_model.predict(X)[0]
        return max(30, int(prediction))
