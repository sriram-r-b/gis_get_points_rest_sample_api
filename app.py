from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry, WKTElement
from geoalchemy2.functions import ST_AsText, ST_Distance
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost/postgres'  # Replace with your database credentials
db = SQLAlchemy(app)

class SpatialData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    location = db.Column(Geometry('POINT', srid=4326), nullable=False) # SRID 4326 for WGS84 (latitude/longitude)

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'latitude': self.location.x,
            'longitude': self.location.y
        }

# Create database tables if they don't exist
with app.app_context():
    db.create_all()


@app.route('/api/points', methods=['POST'])
def create_point():
    try:
        data = request.get_json()
        name = data['name']
        latitude = data['latitude']
        longitude = data['longitude']

        # Create a GeoAlchemy2 WKTElement from the latitude and longitude
        point = WKTElement(f'POINT({longitude} {latitude})', srid=4326) # Note the order: longitude, latitude

        new_point = SpatialData(name=name, location=point)
        db.session.add(new_point)
        db.session.commit()

        return jsonify({'message': 'Point created', 'id': new_point.id}), 201

    except (KeyError, TypeError, ValueError) as e:  # Handle missing/invalid data
        return jsonify({'error': f'Invalid input data: {str(e)}'}), 400
    except Exception as e: # Catch other potential errors
        db.session.rollback() # Rollback in case of database errors
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/api/points/<int:point_id>', methods=['PUT'])
def update_point(point_id):
    try:
        data = request.get_json()
        name = data.get('name')  # Allow updating only name or location or both
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        point = SpatialData.query.get_or_404(point_id)

        if name:
            point.name = name
        if latitude and longitude:
            point.location = WKTElement(f'POINT({longitude} {latitude})', srid=4326)

        db.session.commit()
        return jsonify({'message': 'Point updated'}), 200

    except (KeyError, TypeError, ValueError) as e:
        return jsonify({'error': f'Invalid input data: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/api/points', methods=['GET'])
def get_points():
    try:
        points = SpatialData.query.all()
        point_list = [point.to_json() for point in points]
        return jsonify(point_list), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500



@app.route('/api/points/nearby', methods=['GET'])
def get_nearby_points():
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
        radius = float(request.args.get('radius', 1000))  # Default radius of 1000 meters

        point = WKTElement(f'POINT({longitude} {latitude})', srid=4326)
        nearby_points = SpatialData.query.filter(ST_DWithin(SpatialData.location, point, radius)).all() #ST_DWithin for distance within radius
        point_list = [p.to_json() for p in nearby_points]
        return jsonify(point_list), 200

    except (ValueError, TypeError) as e:
        return jsonify({'error': 'Invalid latitude, longitude, or radius'}), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True)
