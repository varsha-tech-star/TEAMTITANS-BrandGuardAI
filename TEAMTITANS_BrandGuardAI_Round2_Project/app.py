import os, re, sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "brandguard.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-for-deployment")

DEFAULT_RULES = [
    ("Approved wording", "Use the exact approved wording when describing availability.", "available in selected locations", "must_include"),
    ("Avoid absolute claims", "Avoid claims that promise universal availability.", "available everywhere", "must_avoid"),
    ("Preferred term", "Use the preferred product term consistently.", "customers", "prefer"),
    ("Unsupported superlatives", "Superlative claims may need evidence or approval.", "best in the world", "must_avoid"),
]

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, explanation TEXT NOT NULL,
            phrase TEXT NOT NULL, rule_type TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft TEXT NOT NULL, result_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Needs review',
            reviewer_note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )""")
        count = con.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
        if count == 0:
            con.executemany("INSERT INTO rules(title, explanation, phrase, rule_type) VALUES(?,?,?,?)", DEFAULT_RULES)

def analyze_text(draft, rules):
    issues = []
    low = draft.casefold()
    for rule in rules:
        phrase = (rule["phrase"] or "").strip()
        if not phrase:
            continue
        found = phrase.casefold() in low
        rtype = rule["rule_type"]
        if rtype == "must_avoid" and found:
            issues.append({"rule_id": rule["id"], "title": rule["title"], "phrase": phrase,
                           "reason": rule["explanation"], "suggestion": "Remove this wording or replace it with a claim supported by an approved source.", "severity": "Review"})
        elif rtype == "must_include" and not found:
            issues.append({"rule_id": rule["id"], "title": rule["title"], "phrase": phrase,
                           "reason": rule["explanation"], "suggestion": "Check whether the approved wording should be included in this draft.", "severity": "Check"})
        elif rtype == "prefer" and found:
            issues.append({"rule_id": rule["id"], "title": rule["title"], "phrase": phrase,
                           "reason": rule["explanation"], "suggestion": "Confirm this is the preferred term for this audience and context.", "severity": "Suggestion"})
    # Simple accessibility/readability nudges; these are heuristic, not a full audit.
    if re.search(r"https?://\S+", draft) and not re.search(r"\b(link|click|visit|read more)\b", draft, re.I):
        issues.append({"rule_id": None, "title": "Link text may need context", "phrase": "URL",
                       "reason": "A bare URL can be unclear when read by assistive technology or out of context.",
                       "suggestion": "Add descriptive link text that explains where the link goes.", "severity": "Suggestion"})
    if len(draft.split()) > 120:
        issues.append({"rule_id": None, "title": "Long draft", "phrase": "120+ words",
                       "reason": "Long copy can be harder to review quickly.",
                       "suggestion": "Consider splitting the message into shorter paragraphs.", "severity": "Suggestion"})
    return issues

@app.route("/")
def index():
    with connect() as con:
        rules = con.execute("SELECT * FROM rules ORDER BY id DESC").fetchall()
        reviews = con.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT 5").fetchall()
    return render_template("index.html", rules=rules, reviews=reviews)

@app.route("/check", methods=["POST"])
def check():
    draft = request.form.get("draft", "").strip()
    if not draft:
        flash("Paste some content before checking it.", "error")
        return redirect(url_for("index"))
    with connect() as con:
        rules = con.execute("SELECT * FROM rules WHERE active=1 ORDER BY id").fetchall()
        issues = analyze_text(draft, rules)
        status = "Needs review" if issues else "No rule issues found"
        con.execute("INSERT INTO reviews(draft,result_json,status,created_at) VALUES(?,?,?,?)",
                    (draft, json.dumps(issues), status, datetime.now().strftime("%Y-%m-%d %H:%M")))
        review_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    return redirect(url_for("result", review_id=review_id))

@app.route("/result/<int:review_id>")
def result(review_id):
    with connect() as con:
        review = con.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    if not review:
        flash("Review not found.", "error")
        return redirect(url_for("index"))
    return render_template("result.html", review=review, issues=json.loads(review["result_json"]))

@app.route("/rules/add", methods=["POST"])
def add_rule():
    title = request.form.get("title", "").strip()
    explanation = request.form.get("explanation", "").strip()
    phrase = request.form.get("phrase", "").strip()
    rule_type = request.form.get("rule_type", "must_avoid")
    if not title or not explanation or not phrase or rule_type not in {"must_avoid","must_include","prefer"}:
        flash("Please complete every rule field.", "error")
    else:
        with connect() as con:
            con.execute("INSERT INTO rules(title,explanation,phrase,rule_type) VALUES(?,?,?,?)",
                        (title, explanation, phrase, rule_type))
        flash("Brand rule added.", "success")
    return redirect(url_for("index"))

@app.route("/rules/<int:rule_id>/toggle", methods=["POST"])
def toggle_rule(rule_id):
    with connect() as con:
        con.execute("UPDATE rules SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (rule_id,))
    flash("Rule status updated.", "success")
    return redirect(url_for("index"))

@app.route("/review/<int:review_id>/status", methods=["POST"])
def update_status(review_id):
    status = request.form.get("status", "Needs review")
    note = request.form.get("reviewer_note", "").strip()
    if status not in {"Needs review", "Approved by human", "Changes requested"}:
        status = "Needs review"
    with connect() as con:
        con.execute("UPDATE reviews SET status=?, reviewer_note=? WHERE id=?", (status, note, review_id))
    flash("Review decision saved.", "success")
    return redirect(url_for("result", review_id=review_id))

@app.route("/health")
def health():
    return jsonify({"status":"ok", "app":"BrandGuard AI"})

init_db()
if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
