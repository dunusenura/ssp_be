from flask_socketio import SocketIO

# Global SocketIO instance for real-time bi-directional messaging
socketio = SocketIO(cors_allowed_origins="*")

def init_socketio(app):
    """
    Initializes Flask-SocketIO with the Flask application instance.
    """
    socketio.init_app(app, cors_allowed_origins="*")
    return socketio

def emit_event(event_name, data=None):
    """
    Safe helper to emit socket events across all connected clients.
    """
    try:
        socketio.emit(event_name, data or {})
    except Exception as e:
        print(f"Error emitting socket event '{event_name}': {e}")
