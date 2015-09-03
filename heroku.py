from bottle import run
import trebek
import os
import paste

if __name__ == "__main__":
    run(server='paste', host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
