from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import os

# Delete old database if exists
if os.path.exists('tickets.db'):
    os.remove('tickets.db')

# Create database
conn = sqlite3.connect('tickets.db')
conn.execute('''
    CREATE TABLE tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        issue TEXT,
        issue_type TEXT,
        priority TEXT,
        status TEXT DEFAULT 'Open',
        bug INTEGER DEFAULT 0,
        sn_id TEXT,
        jira_id TEXT
    )
''')
conn.close()
print("✅ Database ready")

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/tickets':
            conn = sqlite3.connect('tickets.db')
            rows = conn.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()
            conn.close()
            
            tickets = []
            for r in rows:
                tickets.append({
                    'id': r[0],
                    'name': r[1],
                    'issue': r[2],
                    'issue_type': r[3],
                    'priority': r[4],
                    'status': r[5],
                    'bug': bool(r[6]),
                    'sn_id': r[7],
                    'jira_id': r[8]
                })
            self._send_json(200, tickets)
    
    def do_POST(self):
        if self.path == '/submit':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            
            name = data.get('name', 'Anonymous')
            issue = data.get('issue', '')
            issue_type = data.get('issue_type', 'General')
            priority = data.get('priority', 'Medium')
            
            # Check if bug
            bug_keywords = ['bug', 'error', 'crash', 'broken', 'exception']
            is_bug = any(k in issue.lower() for k in bug_keywords) or issue_type == 'Bug / Technical Error'
            
            # Generate mock IDs
            sn_id = f"INC{abs(hash(issue)) % 10000}"
            jira_id = f"DEV-{abs(hash(issue)) % 5000}" if is_bug else None
            
            # Save to database
            conn = sqlite3.connect('tickets.db')
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO tickets (name, issue, issue_type, priority, bug, sn_id, jira_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, issue, issue_type, priority, 1 if is_bug else 0, sn_id, jira_id))
            
            ticket_id = cur.lastrowid
            conn.commit()
            conn.close()
            
            self._send_json(201, {
                'id': ticket_id,
                'sn_id': sn_id,
                'jira_id': jira_id,
                'is_bug': is_bug
            })
    
    def do_PUT(self):
        if self.path.startswith('/update/'):
            ticket_id = int(self.path.split('/')[-1])
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            new_status = data.get('status')
            
            conn = sqlite3.connect('tickets.db')
            conn.execute('UPDATE tickets SET status = ? WHERE id = ?', (new_status, ticket_id))
            conn.commit()
            conn.close()
            
            self._send_json(200, {'id': ticket_id, 'status': new_status})

print("\n" + "="*50)
print("🚀 SERVER RUNNING on http://localhost:5000")
print("📋 Test API: http://localhost:5000/tickets")
print("="*50 + "\n")

HTTPServer(('localhost', 5000), Handler).serve_forever()