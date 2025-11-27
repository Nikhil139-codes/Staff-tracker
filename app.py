# app.py
from flask import Flask, jsonify, render_template, request
import sqlite3, json, os, time

app = Flask(__name__)

DB = "attendance.db"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/rooms')
def rooms():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT id, room_name, source_url FROM cameras")
    cams = c.fetchall()
    out = []
    for cam in cams:
        cam_id, room_name, src = cam
        c.execute("SELECT pi.start_time, pi.end_time, t.name FROM presence_intervals pi JOIN teachers t ON pi.teacher_id=t.id WHERE pi.camera_id=? ORDER BY COALESCE(pi.end_time, pi.start_time) DESC LIMIT 1", (cam_id,))
        r = c.fetchone()
        if r:
            ts = r[1] if r[1] is not None else r[0]
            name = r[2]
            last = {"teacher":name, "timestamp":ts}
        else:
            last = None
        out.append({"camera_id":cam_id,"room_name":room_name,"source":src,"last_seen":last})
    conn.close()
    return jsonify(out)

@app.route('/api/teacher/<name>/current')
def teacher_current(name):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT COALESCE(end_time, start_time) as last_ts, cam.room_name FROM presence_intervals pi JOIN teachers t ON pi.teacher_id=t.id JOIN cameras cam ON pi.camera_id=cam.id WHERE t.name=? ORDER BY last_ts DESC LIMIT 1", (name,))
    r = c.fetchone(); conn.close()
    if r:
        return jsonify({"teacher":name,"room_name":r[1],"timestamp":r[0]})
    else:
        return jsonify({"teacher":name,"room_name":None,"timestamp":None})

@app.route('/api/teacher/<name>/timeline')
def teacher_timeline(name):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT pi.start_time, pi.end_time, cam.room_name FROM presence_intervals pi JOIN teachers t ON pi.teacher_id=t.id JOIN cameras cam ON pi.camera_id=cam.id WHERE t.name=? ORDER BY pi.start_time ASC", (name,))
    rows = [{"start":r[0],"end":r[1],"room":r[2]} for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    # if cams.json exists, insert cameras into DB
    if os.path.exists("cams.json"):
        with open("cams.json") as f:
            cams = json.load(f)
        conn = sqlite3.connect(DB); c = conn.cursor()
        for cam in cams:
            c.execute("INSERT OR IGNORE INTO cameras (id, room_name, source_url) VALUES (?, ?, ?)", (cam["id"], cam["room_name"], cam["source"]))
        conn.commit(); conn.close()
    app.run(host='0.0.0.0', port=5000, debug=True)
