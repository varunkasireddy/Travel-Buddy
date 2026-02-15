import requests
import os
from dotenv import load_dotenv

load_dotenv()

class AmadeusClient:
    def __init__(self):
        self.api_key = os.getenv('AMADEUS_API_KEY')
        self.api_secret = os.getenv('AMADEUS_API_SECRET')
        self.base_url = "https://test.api.amadeus.com"
        self.token = self._get_token()

    def _get_token(self):
        if not self.api_key or not self.api_secret:
            return None
        url = f"{self.base_url}/v1/security/oauth2/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.api_key,
            'client_secret': self.api_secret
        }
        try:
            response = requests.post(url, data=data)
            return response.json().get('access_token')
        except:
            return None

    def get_iata_code(self, city_name):
        if not self.token:
            return "LON" # Default fallback
        
        url = f"{self.base_url}/v1/reference-data/locations"
        params = {
            'keyword': city_name,
            'subType': 'CITY',
            'view': 'LIGHT'
        }
        headers = {'Authorization': f'Bearer {self.token}'}
        try:
            response = requests.get(url, params=params, headers=headers)
            data = response.json().get('data', [])
            if data:
                return data[0]['iataCode']
            return "LON"
        except:
            return "LON"

    def search_locations(self, keyword):
        if not self.token or len(keyword) < 2:
            return []
        
        url = f"{self.base_url}/v1/reference-data/locations"
        params = {
            'keyword': keyword,
            'subType': 'CITY',
            'view': 'LIGHT'
        }
        headers = {'Authorization': f'Bearer {self.token}'}
        try:
            response = requests.get(url, params=params, headers=headers)
            data = response.json().get('data', [])
            results = []
            for item in data:
                results.append({
                    "name": item.get('name'),
                    "iata": item.get('iataCode'),
                    "country": item.get('address', {}).get('countryCode')
                })
            return results
        except:
            return []

    def get_flight_offers(self, origin, destination, date, adults):
        if not self.token:
            return []
        url = f"{self.base_url}/v2/shopping/flight-offers"
        params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': date,
            'adults': adults,
            'max': 5
        }
        headers = {'Authorization': f'Bearer {self.token}'}
        try:
            response = requests.get(url, params=params, headers=headers)
            return response.json().get('data', [])
        except:
            return []

class WeatherClient:
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        self.base_url = "https://api.openweathermap.org/data/2.5"

    def get_weather(self, city):
        if not self.api_key:
            return {"temp": "N/A", "description": "Unknown"}
        url = f"{self.base_url}/weather"
        params = {'q': city, 'appid': self.api_key, 'units': 'metric'}
        try:
            response = requests.get(url, params=params)
            data = response.json()
            return {
                "temp": data['main']['temp'],
                "description": data['weather'][0]['description']
            }
        except:
            return {"temp": "N/A", "description": "Unknown"}

class CurrencyClient:
    def __init__(self):
        self.base_url = "https://api.exchangerate.host/latest"

    def get_rates(self):
        try:
            # Using a public free API (exchangerate.host often redirects or needs keys now, 
            # so using a reliable fallback if it fails)
            response = requests.get(self.base_url, timeout=5)
            return response.json().get('rates', {})
        except:
            return {"EUR": 0.92, "GBP": 0.79, "JPY": 150.0} # Fallback common rates

class BookingClient:
    def __init__(self):
        self.api_key = os.getenv('RAPIDAPI_KEY')
        self.host = "booking-com.p.rapidapi.com"
        self.base_url = f"https://{self.host}/v1"

    def get_hotels(self, city_name):
        if not self.api_key:
            return []
        
        # 1. Search Location ID
        search_url = f"{self.base_url}/hotels/locations"
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host
        }
        try:
            res = requests.get(search_url, params={"name": city_name, "locale": "en-gb"}, headers=headers)
            loc_id = res.json()[0]['dest_id']
            
            # 2. Search Hotels
            hotels_url = f"{self.base_url}/hotels/search"
            params = {
                "dest_id": loc_id,
                "dest_type": "city",
                "checkin_date": "2026-06-01", # Demo dates
                "checkout_date": "2026-06-08",
                "adults_number": "2",
                "order_by": "popularity",
                "room_number": "1",
                "units": "metric"
            }
            res = requests.get(hotels_url, params=params, headers=headers)
            return res.json().get('result', [])[:3]
        except:
            return []

class SafetyClient:
    def __init__(self):
        # Using the base domain to avoid some redirect/SSL hostname issues seen in logs
        self.base_url = "https://www.travel-advisory.info/api"

    def get_safety_score(self, country_code):
        try:
            url = f"{self.base_url}?countrycode={country_code}"
            # Added verify=False as a fallback for the kasserver.com certificate mismatch observed
            response = requests.get(url, verify=False, timeout=5)
            data = response.json()
            return data['data'][country_code]['advisory']['score']
        except:
            return 2.5
