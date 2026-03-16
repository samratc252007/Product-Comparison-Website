from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS
import http.client
import urllib.parse
import json
import requests
import sqlite3
import json
import requests
import sqlite3
import os
import time

app = Flask(__name__)
CORS(app)
# Secure secret key for sessions
app.secret_key = os.urandom(24)

# ============================
# Database Setup
# ============================
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            unblock_time REAL DEFAULT 0
        )
    ''')
    
    # Try gracefully adding the new columns if the table already existed from before
    try:
        c.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    except sqlite3.OperationalError:
        pass # Column likely already exists
        
    try:
        c.execute("ALTER TABLE users ADD COLUMN unblock_time REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column likely already exists
        
    c.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
        
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ============================
# Amazon Data Fetch Function
# ============================
def fetch_amazon_data(query):
    conn = http.client.HTTPSConnection("real-time-amazon-data.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "d2a3347ee3mshfd391c22e98682dp1ede0cjsn1a6fcb47cbbf",
        'x-rapidapi-host': "real-time-amazon-data.p.rapidapi.com"
    }

    encoded_query = urllib.parse.quote(query)
    conn.request("GET", f"/search?query={encoded_query}&country=US", headers=headers)
    
    res = conn.getresponse()
    data = res.read()
    decoded_data = data.decode("utf-8")

    try:
        response_data = json.loads(decoded_data)
        if "data" in response_data and "products" in response_data["data"]:
            return response_data["data"]["products"]
        return []
    except json.JSONDecodeError:
        print("Failed to parse Amazon API response")
        return []

# ============================
# Walmart Data Fetch Function
# ============================
def fetch_walmart_data(query):
    url = "https://realtime-walmart-data.p.rapidapi.com/search"

    querystring = {
        "keyword": query,
        "page": "1",
        "sort": "price_high"
    }

    headers = {
        'x-rapidapi-key': "d2a3347ee3mshfd391c22e98682dp1ede0cjsn1a6fcb47cbbf",
        'x-rapidapi-host': "realtime-walmart-data.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        response_data = response.json()

        products = response_data.get("results", [])

        if not isinstance(products, list):
            return []

        normalized_products = []
        for item in products:
            normalized_products.append({
                "title": item.get("name"),
                "image": item.get("image"),
                "link": item.get("canonicalUrl"),
                "price": {
                    "currentPrice": item.get("price"),
                    "originalPrice": item.get("originalPrice")
                },
                "ratings": item.get("rating"),
                "reviewsCount": item.get("numberOfReviews"),
                "shippingMessage": item.get("availability")
            })
        return normalized_products

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Walmart data: {e}")
        return []
    except json.JSONDecodeError:
        print("JSON decode error in Walmart response")
        return []

# ============================
# Landing Page Route
# ============================
# Landing Page Route
# ============================
@app.route('/')
def home():
    auth_action = request.args.get('auth_action')
    auth_error = request.args.get('auth_error')
    
    current_streak = 0
    if 'username' in session:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
        user = c.fetchone()
        
        if user:
            user_id = user[0]
            # Get distinct dates the user searched, ordered descending
            c.execute('''
                SELECT DISTINCT date(timestamp) 
                FROM search_history 
                WHERE user_id = ? 
                ORDER BY date(timestamp) DESC
            ''', (user_id,))
            dates = [row[0] for row in c.fetchall()]
            
            import datetime
            today = datetime.datetime.utcnow().date()
            
            streak = 0
            check_date = today
            
            # If they searched today, start streak counting from today
            if dates and dates[0] == str(today):
                for d in dates:
                    if d == str(check_date):
                        streak += 1
                        check_date -= datetime.timedelta(days=1)
                    else:
                        break
            # If they haven't searched today, check if they searched yesterday
            elif dates and dates[0] == str(today - datetime.timedelta(days=1)):
                check_date = today - datetime.timedelta(days=1)
                for d in dates:
                    if d == str(check_date):
                        streak += 1
                        check_date -= datetime.timedelta(days=1)
                    else:
                        break
            
            current_streak = streak
            
        conn.close()

    return render_template('home.html', auth_action=auth_action, auth_error=auth_error, current_streak=current_streak)

# ============================
# Comparison Page Route
# ============================
@app.route('/compare', methods=['GET', 'POST'])
def compare():
    # Enforce premium logged-in access
    if 'username' not in session:
        flash("Unlock the power of Codesky. Sign up to start comparing!", "error")
        return redirect(url_for('signup'))

    amazon_results = []
    walmart_results = []
    query = ""
    # Retrieve query parameter from URL if present (for recent searches re-run)
    if 'query' in request.args:
        query = request.args.get('query').strip()
        amazon_results = fetch_amazon_data(query)
        walmart_results = fetch_walmart_data(query)
        
        # Save GET requests to search history if authenticated (smart suggestions/recent searches)
        if 'username' in session and query:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
            user = c.fetchone()
            if user:
                c.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)", (user[0], query.lower()))
                conn.commit()
            conn.close()

    if request.method == 'POST':
        query = request.form['query'].strip()
        amazon_results = fetch_amazon_data(query)
        walmart_results = fetch_walmart_data(query)

        if 'username' in session and query:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
            user = c.fetchone()
            if user:
                c.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)", (user[0], query.lower()))
                conn.commit()
            conn.close()

    return render_template('index.html', amazon=amazon_results, walmart=walmart_results, query=query)

# ============================
# Authentication Routes
# ============================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    import re
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Backend Validation
        if not re.match(r"^[a-zA-Z0-9]+$", username):
            flash("Username must contain only letters and numbers without spaces or special characters.", "error")
            return redirect(url_for('signup'))
            
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$", password):
            flash("Password must be at least 8 characters long and include an uppercase letter, a lowercase letter, a number, and a special character.", "error")
            return redirect(url_for('signup'))
        
        # USER REQUESTED CHANGE: Storing passwords in plaintext so the admin can view them directly.
        # WARNING: Not recommended for production.
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                      (username, email, password))
            conn.commit()
            conn.close()
            
            session['username'] = username
            session['show_welcome_animation'] = True
            
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            flash("Username or Email already exists", "error")
            return redirect(url_for('signup'))
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT id, username, password, status, unblock_time FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        # Check against raw text since we reverted generating hashes.
        if user and user[2] == password:
            user_id = user[0]
            username = user[1]
            status = user[3]
            unblock_time = user[4]
            
            if status == 'suspended_lifetime':
                flash("Your account has been permanently suspended.", "error")
                return redirect(url_for('login'))
            elif status == 'suspended_24h':
                if time.time() < unblock_time:
                    flash("You are suspended for 24 hours. Please try again later.", "error")
                    return redirect(url_for('login'))
                else:
                    # Suspension period is over, clear it
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    c.execute("UPDATE users SET status = 'active', unblock_time = 0 WHERE id = ?", (user_id,))
                    conn.commit()
                    conn.close()

            session['username'] = username
            session['show_welcome_animation'] = True
            
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for('login'))
            
    return render_template('login.html')

# ============================
# Admin Routes
# ============================
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'welcomeadmin':
            session['admin_logged_in'] = True
            session['show_admin_welcome'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin credentials", "error")
            return redirect(url_for('admin_login'))
            
    return render_template('admin_login.html')

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, email, password, status, unblock_time FROM users")
    users = c.fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin_action/<int:user_id>/<action>', methods=['POST'])
def admin_action(user_id, action):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    if action == 'delete':
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        flash(f"User #{user_id} deleted successfully.", "success")
    elif action == 'suspend_24h':
        unblock_time = time.time() + (24 * 60 * 60)
        c.execute("UPDATE users SET status = 'suspended_24h', unblock_time = ? WHERE id = ?", (unblock_time, user_id))
        flash(f"User #{user_id} suspended for 24 hours.", "success")
    elif action == 'suspend_lifetime':
        c.execute("UPDATE users SET status = 'suspended_lifetime', unblock_time = 0 WHERE id = ?", (user_id,))
        flash(f"User #{user_id} permanently suspended.", "success")
    elif action == 'unsuspend':
        c.execute("UPDATE users SET status = 'active', unblock_time = 0 WHERE id = ?", (user_id,))
        flash(f"User #{user_id} unsuspended.", "success")
        
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login', logged_out=1))

@app.route('/clear_welcome_flag')
def clear_welcome_flag():
    session.pop('show_welcome_animation', None)
    return '', 204

@app.route('/clear_admin_welcome_flag')
def clear_admin_welcome_flag():
    session.pop('show_admin_welcome', None)
    return '', 204

@app.route('/api/search_stats')
def api_search_stats():
    if not session.get('admin_logged_in'):
        return {"error": "Unauthorized"}, 401

    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Query 1: Top 5 Active Users
    c.execute('''
        SELECT u.username, COUNT(s.id) as search_count 
        FROM users u 
        JOIN search_history s ON u.id = s.user_id 
        GROUP BY u.id 
        ORDER BY search_count DESC 
        LIMIT 5
    ''')
    top_users = [dict(row) for row in c.fetchall()]

    # Query 2: Top 5 Most Searched Queries
    c.execute('''
        SELECT query, COUNT(*) as count 
        FROM search_history 
        GROUP BY query 
        ORDER BY count DESC 
        LIMIT 5
    ''')
    top_queries = [dict(row) for row in c.fetchall()]

    conn.close()
    return {"top_users": top_users, "top_queries": top_queries}

@app.route('/api/my_search_stats')
def api_my_search_stats():
    if 'username' not in session:
        return {"error": "Unauthorized"}, 401
    
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get user id
    c.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
    user = c.fetchone()
    if not user:
        conn.close()
        return {"error": "User not found"}, 404
        
    user_id = user['id']
    
    # Get top 5 unique searches for this specific user
    c.execute('''
        SELECT query, COUNT(*) as count 
        FROM search_history 
        WHERE user_id = ?
        GROUP BY query 
        ORDER BY count DESC 
        LIMIT 5
    ''', (user_id,))
    
    my_top_queries = [dict(row) for row in c.fetchall()]
    
    # Also get 5 most recent searches
    c.execute('''
        SELECT query, timestamp
        FROM search_history
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
    ''', (user_id,))
    recent_searches = [dict(row) for row in c.fetchall()]

    conn.close()
    return {"top_queries": my_top_queries, "recent": recent_searches}

@app.route('/api/extension/compare')
def api_extension_compare():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    amazon_results = fetch_amazon_data(query)
    walmart_results = fetch_walmart_data(query)
    
    return jsonify({
        "amazon": amazon_results,
        "walmart": walmart_results
    })

app.config['API_KEYS'] = {
    'amazon': 'e6caeb79bdecf3a9bd4828b6d05f3fc5c327ec29dbe06990de8fe78df4958ce1',
    'walmart': '0597af65c6352effb1f4c7185aabaf003f42b31e9c20a969f6eeb248b61e2a07'
}

# ============================
# Run the Flask App
# ============================
if __name__ == '__main__':
    init_db()
    # To run fetch_and_save continuously in the background:(debug=True)
    app.run(debug=True)
