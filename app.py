from flask import Flask
from flask_cors import CORS
import config
from database import init_db
from socket_service import init_socketio, socketio
from routes.auth_routes import auth_bp
from routes.job_routes import job_bp
from routes.booking_routes import booking_bp
from routes.payment_routes import payment_bp
from routes.chat_routes import chat_bp
from routes.user_routes import user_bp
from routes.review_routes import review_bp
from routes.admin_routes import admin_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    
    # Configure CORS
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS,PATCH')
        return response

    # Initialize Database
    init_db(app)

    # Initialize Socket.IO
    init_socketio(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(job_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(admin_bp)

    return app

app = create_app()

if __name__ == '__main__':
    print(f"WorkPub Backend Server starting on port {config.PORT} with Socket.IO...")
    socketio.run(app, debug=config.DEBUG, host='0.0.0.0', port=config.PORT, allow_unsafe_werkzeug=True)