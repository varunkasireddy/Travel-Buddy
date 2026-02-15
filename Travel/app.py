from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from utils import TravelRecommender, AmadeusClient, BookingClient

app = Flask(__name__, static_folder='static')
CORS(app)

recommender = TravelRecommender()
print(f"Travel Buddy Initialized: {len(recommender.df)} destinations loaded.")
amadeus = AmadeusClient()
booking = BookingClient()

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/extra-details', methods=['POST'])
def extra_details():
    data = request.json
    city = data.get('city')
    country_code = data.get('country_code')
    origin_city = data.get('origin_city', 'London')
    
    # In a real app, you'd map city to IATA code
    # For demo, we'll try to get flight offers if we have an IATA-like code or mock
    flights = []
    if amadeus.token:
        # Resolve Origin IATA
        origin_iata = amadeus.get_iata_code(origin_city)
        # Mock Destination IATA logic (first 3 chars) or use API if we had a robust city->iata mapper
        dest_iata = city[:3].upper() 
        flights = amadeus.get_flight_offers(origin_iata, dest_iata, '2026-06-01', 1)
        
    hotels = booking.get_hotels(city)
    
    return jsonify({
        "flights": flights[:2],
        "hotels": hotels,
        "origin_iata": origin_iata if amadeus.token else "N/A"
    })

@app.route('/api/city-search', methods=['GET'])
def city_search():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify([])
    
    if amadeus.token:
        results = amadeus.search_locations(keyword)
        return jsonify(results)
    
    # Mock fallback if no API key
    return jsonify([
        {"name": "London", "iata": "LON", "country": "GB"},
        {"name": "New York", "iata": "NYC", "country": "US"},
        {"name": "Paris", "iata": "PAR", "country": "FR"}
    ])

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.json
    continent = data.get('continent')
    budget = data.get('budget', 1000)
    currency = data.get('currency', 'USD')
    days = int(data.get('days', 7))
    people = int(data.get('people', 1))
    origin_city = data.get('origin_city', 'London')
    
    print(f"Received request: {data}")
    
    recommendations = recommender.recommend(continent, budget, days, people, currency, origin_city)
    
    return jsonify(recommendations)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
