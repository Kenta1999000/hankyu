from flask import Flask, request, jsonify, render_template
import pandas as pd
import heapq

app = Flask(__name__)

# ============================================================
# 1. 駅一覧（正式名称）
# ============================================================
STATIONS = [
    # 神戸本線
    "大阪梅田","中津","十三","神崎川","園田","塚口","武庫之荘","西宮北口","夙川",
    "芦屋川","岡本","御影","六甲","王子公園","春日野道","神戸三宮",

    # 宝塚本線
    "三国","庄内","服部天神","曽根","岡町","豊中","蛍池","石橋阪大前","池田",
    "川西能勢口","雲雀丘花屋敷","山本","中山観音","売布神社","清荒神","宝塚",

    # 箕面線
    "桜井","牧落","箕面",

    # 京都本線
    "南方","崇禅寺","淡路","上新庄","相川","正雀","摂津市","南茨木","茨木市",
    "総持寺","富田","高槻市","上牧","水無瀬","大山崎","長岡天神",
    "西山天王山","桂","西京極","西院","大宮","烏丸","京都河原町",

    # 千里線
    "天神橋筋六丁目","柴島","下新庄","吹田","豊津","江坂",
    "南千里","千里山","関大前","北千里",

    # 今津線
    "宝塚南口","逆瀬川","小林","仁川","甲東園","門戸厄神","阪神国道","今津",

    # 伊丹線
    "稲野","新伊丹","伊丹",

    # 甲陽線
    "苦楽園口","甲陽園",

    # 嵐山線
    "上桂","松尾大社","嵐山",
]

# ============================================================
# 2. 線路接続データ（隣駅）
# ============================================================
EDGES = [
    ("大阪梅田","中津"),("中津","十三"),
    ("十三","神崎川"),("神崎川","園田"),("園田","塚口"),
    ("塚口","武庫之荘"),("武庫之荘","西宮北口"),("西宮北口","夙川"),
    ("夙川","芦屋川"),("芦屋川","岡本"),("岡本","御影"),("御影","六甲"),
    ("六甲","王子公園"),("王子公園","春日野道"),("春日野道","神戸三宮"),

    ("十三","三国"),("三国","庄内"),("庄内","服部天神"),("服部天神","曽根"),
    ("曽根","岡町"),("岡町","豊中"),("豊中","蛍池"),("蛍池","石橋阪大前"),
    ("石橋阪大前","池田"),("池田","川西能勢口"),("川西能勢口","雲雀丘花屋敷"),
    ("雲雀丘花屋敷","山本"),("山本","中山観音"),("中山観音","売布神社"),
    ("売布神社","清荒神"),("清荒神","宝塚"),

    ("石橋阪大前","桜井"),("桜井","牧落"),("牧落","箕面"),

    ("十三","南方"),("南方","崇禅寺"),("崇禅寺","淡路"),
    ("淡路","上新庄"),("上新庄","相川"),("相川","正雀"),("正雀","摂津市"),
    ("摂津市","南茨木"),("南茨木","茨木市"),("茨木市","総持寺"),
    ("総持寺","富田"),("富田","高槻市"),("高槻市","上牧"),
    ("上牧","水無瀬"),("水無瀬","大山崎"),("大山崎","長岡天神"),
    ("長岡天神","西山天王山"),("西山天王山","桂"),
    ("桂","西京極"),("西京極","西院"),("西院","大宮"),("大宮","烏丸"),
    ("烏丸","京都河原町"),

    ("天神橋筋六丁目","柴島"),("柴島","淡路"),("淡路","下新庄"),
    ("下新庄","吹田"),("吹田","豊津"),("豊津","江坂"),
    ("江坂","南千里"),("南千里","千里山"),("千里山","関大前"),("関大前","北千里"),

    ("宝塚","宝塚南口"),("宝塚南口","逆瀬川"),("逆瀬川","小林"),
    ("小林","仁川"),("仁川","甲東園"),("甲東園","門戸厄神"),
    ("門戸厄神","西宮北口"),("西宮北口","阪神国道"),("阪神国道","今津"),

    ("塚口","稲野"),("稲野","新伊丹"),("新伊丹","伊丹"),

    ("西宮北口","苦楽園口"),("苦楽園口","甲陽園"),

    ("桂","上桂"),("上桂","松尾大社"),("松尾大社","嵐山")
]

# ============================================================
# 3. 駅間キロ数 Excel（営業キロマトリクス）ロード
# ============================================================
def load_hankyu_distance_matrix(path="hankyu_kilo_official.xlsx"):
    df = pd.read_excel(path)

    stations = df.iloc[:, 0].astype(str).tolist()
    cols = df.columns.tolist()[1:]

    dist = {}
    for i, a in enumerate(stations):
        for j, b in enumerate(cols):
            km = df.iloc[i, j+1]
            if pd.isna(km):
                continue
            dist[(a.strip(), b.strip())] = float(km)

    return dist

DIST_TABLE = load_hankyu_distance_matrix()


# ============================================================
# 4. グラフ構築（隣駅 × 距離は Excel）
# ============================================================
def build_graph():
    graph = {s: [] for s in STATIONS}

    for a, b in EDGES:
        km = DIST_TABLE.get((a, b))
        if km is None:
            km = 1.0  # 基本出ない
        graph[a].append((b, km))
        graph[b].append((a, km))
    return graph

GRAPH = build_graph()


# ============================================================
# 5. ダイクストラ（距離最短）
# ============================================================
def dijkstra_distance(start, goal):
    pq = [(0.0, start, [])]
    visited = set()

    while pq:
        dist, station, path = heapq.heappop(pq)

        if station == goal:
            return dist, path + [station]

        if station in visited:
            continue
        visited.add(station)

        for next_st, km in GRAPH[station]:
            heapq.heappush(pq, (dist + km, next_st, path + [station]))

    return None, None


# ============================================================
# 6. 営業キロ別運賃（あなたが指定した区分）
# ============================================================
def calc_fare(km):
    if km <= 4:
        return 170
    elif km <= 9:
        return 200
    elif km <= 14:
        return 240
    elif km <= 19:
        return 280
    elif km <= 26:
        return 290
    elif km <= 33:
        return 330
    elif km <= 42:
        return 390
    elif km <= 51:
        return 410
    elif km <= 60:
        return 480
    elif km <= 70:
        return 540
    else:
        return 640


# ============================================================
# 7. API: 駅一覧
# ============================================================
@app.route("/hankyu/stations")
def station_list():
    return jsonify(sorted(STATIONS))


# ============================================================
# 8. API: 区間の運賃計算（途中下車対応）
# ============================================================
@app.route("/hankyu/calc")
def calc_multi():

    start = request.args.get("start")
    goal  = request.args.get("goal")
    stops_param = request.args.get("stops", "")

    if not start or not goal:
        return jsonify({"error": "start と goal は必須"}), 400

    stops = [s for s in stops_param.split(",") if s]
    journey = [start] + stops + [goal]

    total_km = 0.0
    total_fare = 0
    details = []

    for i in range(len(journey)-1):
        a = journey[i]
        b = journey[i+1]

        km, route = dijkstra_distance(a, b)

        if route is None:
            return jsonify({"error": f"{a} → {b} の経路が見つかりません"}), 404

        fare = calc_fare(km)
        total_km += km
        total_fare += fare

        details.append({
            "start": a,
            "goal": b,
            "distance_km": round(km, 1),
            "fare": fare
        })

    return jsonify({
        "journey_order": journey,
        "total_distance_km": round(total_km, 1),
        "total_fare": total_fare,
        "details": details
    })


# ============================================================
# 9. UI（LIFF用 index.html）
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/routes")
def debug_route():
    return render_template("routes.html")


# ============================================================
# 10. Flask 実行
# ============================================================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
