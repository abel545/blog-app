import os
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON 환경변수가 없습니다.")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sheet = client.open_by_key(spreadsheet_id).sheet1
    return sheet


# ── 메인 (게시물 목록) ────────────────────────────────────────
@app.route("/")
def index():
    sheet = get_sheet()
    rows = sheet.get_all_records()

    # 최신순 정렬
    rows = list(reversed(rows))

    # 번호 부여 (상세 페이지용)
    total = len(rows)
    for i, row in enumerate(rows):
        row["row_index"] = total - i  # 실제 시트 행 번호 (1부터)

    return render_template("index.html", posts=rows)


# ── 글쓰기 페이지 ─────────────────────────────────────────────
@app.route("/write")
def write():
    return render_template("write.html")


# ── 게시물 제출 ───────────────────────────────────────────────
@app.route("/submit", methods=["POST"])
def submit():
    title    = request.form.get("title", "").strip()
    author   = request.form.get("author", "").strip()
    category = request.form.get("category", "").strip()
    content  = request.form.get("content", "").strip()

    if not all([title, author, content]):
        return "제목, 작성자, 내용은 필수입니다.", 400

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet = get_sheet()
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(["번호", "타임스탬프", "제목", "작성자", "카테고리", "내용", "조회수"])

    # 번호 자동 증가
    all_rows = sheet.get_all_records()
    next_id = len(all_rows) + 1

    sheet.append_row([next_id, timestamp, title, author, category, content, 0])

    return redirect(url_for("index"))


# ── 게시물 상세보기 ───────────────────────────────────────────
@app.route("/post/<int:post_id>")
def post_detail(post_id):
    sheet = get_sheet()
    all_rows = sheet.get_all_records()

    # post_id로 게시물 찾기
    post = None
    row_num = None
    for i, row in enumerate(all_rows):
        if int(row.get("번호", 0)) == post_id:
            post = row
            row_num = i + 2  # 헤더 제외, 1-indexed
            break

    if not post:
        return "게시물을 찾을 수 없습니다.", 404

    # 조회수 증가
    try:
        current_views = int(post.get("조회수", 0))
        # 조회수 열은 7번째 (G열)
        sheet.update_cell(row_num, 7, current_views + 1)
        post["조회수"] = current_views + 1
    except Exception:
        pass

    return render_template("post.html", post=post)


# ── 게시물 삭제 ───────────────────────────────────────────────
@app.route("/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    sheet = get_sheet()
    all_rows = sheet.get_all_records()

    row_num = None
    for i, row in enumerate(all_rows):
        if int(row.get("번호", 0)) == post_id:
            row_num = i + 2
            break

    if row_num:
        sheet.delete_rows(row_num)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
