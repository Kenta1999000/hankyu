from flask import Flask, request, jsonify, send_from_directory
import csv

app = Flask(__name__)

########################################
# 1. CSV から駅間キロを読み込み（マトリクス形式）
########################################

KILO_CSV = "hankyu_kilo_official.csv"   # プロジェクトのルートに置いておく

# (駅A, 駅B) -> km の辞書
edge_km = {}
ALL_STATIONS = []


def load_kilo_csv():
    """駅×駅の距離マトリクスCSVを読み込んで edge_km を構築"""
    global edge_km, ALL_STATIONS
    edge_km = {}
    ALL_STATIONS = []

    try:
        # Windows で作った CSV っぽいので cp932 で読む
        with open(KILO_CSV, encoding="cp932") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            print("CSV が空です")
            return

        # 1行目：列ヘッダー（駅名）、先頭セルは空想定
        header = rows[0]
        col_stations = [name.strip() for name in header[1:]]

        # 2行目以降：行ヘッダー + 距離
        row_stations = []

        for r in rows[1:]:
            if not r:
                continue
            row_station = r[0].strip()
            if not row_station:
                continue
            row_stations.append(row_station)

            # r[1:] がこの行の距離（列ヘッダーと対応）
            for i, cell in enumerate(r[1:]):
                if i >= len(col_stations):
                    break
                col_station = col_stations[i]
                cell = cell.strip()

                if cell == "" or cell == "-":
                    continue

                try:
                    km = float(cell)
                except ValueError:
                    continue

                # 双方向に登録
                edge_km[(row_station, col_station)] = km
                edge_km[(col_station, row_station)] = km

        # 駅一覧は行ヘッダー + 列ヘッダーのユニーク集合
        ALL_STATIONS = sorted(set(row_stations) | set(col_stations))

        print("CSV 読み込み成功:", len(ALL_STATIONS), "駅,", len(edge_km), "区間")

    except Exception as e:
        # Windowsコンソールで絵文字が死ぬので日本語だけにする
        print("CSV 読み込み失敗:", e)


# 起動時に一度読み込む
load_kilo_csv()

########################################
# 2. 阪急運賃計算（営業キロ→運賃）
########################################

def calc_hankyu_fare(total_km: float) -> int:
    """
    営業キロ数から阪急運賃を返す。
    区間ごとに適用（端数はそのまま距離として扱う）。
    """
    if total_km <= 6:
        return 170
    elif total_km <= 10:
        return 200
    elif total_km <= 16:
        return 240
    elif total_km <= 21:
        return 280
    elif total_km <= 26:
        return 320
    elif total_km <= 31:
        return 360
    elif total_km <= 36:
        return 400
    elif total_km <= 41:
        return 440
    elif total_km <= 46:
        return 480
    else:
        return 520


########################################
# 3. 区間の距離を取り出す（マトリクス辞書から）
########################################

def compute_segment_km(start: str, goal: str):
    """
    start→goal の営業キロを edge_km から返す。
    データがなければ None。
    """
    key = (start, goal)
    return edge_km.get(key)


########################################
# 4. 旅程全体（途中下車含む）の計算
########################################

def compute_journey(start: str, stops: list[str], goal: str):
    """
    [start] -> [途中下車…] -> [goal] の順に駅を回る旅程の
    ・各区間の距離と運賃
    ・合計運賃
    ・一日券との比較
    を計算して dict で返す。
    """
    order = [start] + stops + [goal]

    details = []
    total_fare = 0
    total_km_sum = 0.0

    for i in range(len(order) - 1):
        s = order[i]
        g = order[i + 1]

        km = compute_segment_km(s, g)
        if km is None:
            return {"error": f"{s} → {g} のキロ数が CSV にありません"}

        fare = calc_hankyu_fare(km)
        total_fare += fare
        total_km_sum += km

        details.append({
            "start": s,
            "goal": g,
            "distance_km": km,
            "fare": fare
        })

    ONE_DAY_PASS = 1300
    if total_fare > ONE_DAY_PASS:
        recommendation = "1日乗車券の方が安いです"
    elif total_fare < ONE_DAY_PASS:
        recommendation = "通常運賃の方が安いです"
    else:
        recommendation = "どちらも同じ金額です"

    return {
        "journey_order": order,
        "details": details,
        "total_km": total_km_sum,
        "total_fare": total_fare,
        "one_day_pass": ONE_DAY_PASS,
        "recommendation": recommendation,
    }


########################################
# 5. API: 駅一覧
########################################

@app.route("/hankyu/stations")
def get_stations():
    # index.html の駅プルダウン用
    return jsonify(ALL_STATIONS)


########################################
# 6. API: 運賃計算
########################################

@app.route("/hankyu/calc")
def calc():
    start = request.args.get("start")
    goal = request.args.get("goal")
    stops_raw = request.args.get("stops", "")

    if not start or not goal:
        return jsonify({"error": "start と goal は必須です"})

    stops = [s for s in stops_raw.split(",") if s]

    # 入力駅が CSV の駅一覧に存在するか簡単チェック
    for st in [start, goal] + stops:
        if st not in ALL_STATIONS:
            return jsonify({"error": f"駅『{st}』はキロ表に存在しません"})

    result = compute_journey(start, stops, goal)
    return jsonify(result)


########################################
# 7. index.html を返す
########################################

@app.route("/")
def index():
    # 同じディレクトリにある index.html を返す
    return send_from_directory(".", "templates/index.html")


########################################
# 8. ローカル実行用エントリ
########################################

if __name__ == "__main__":
    # ローカルテスト用： http://127.0.0.1:8080/
    app.run(host="0.0.0.0", port=8080, debug=True)
