import os
from app import create_app

app = create_app('production' if os.getenv('FLASK_ENV') == 'production' else 'default')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5330))
    app.run(debug=True, host='0.0.0.0', port=port)
