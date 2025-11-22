from flask import Flask, request, jsonify, render_template
import heapq
app = Flask(__name__)

# ============================================
# 阪急電鉄 全線 STATIONS / EDGES データセット
# ============================================

# ---- 1. 神戸本線 ----
kobe_main = [
    "大阪梅田", "中津", "十三", "神崎川", "園田", "塚口", "武庫之荘",
    "西宮北口", "夙川", "芦屋川", "岡本", "御影", "六甲",
    "王子公園", "春日野道", "神戸三宮"
]
kobe_main_edges = [(kobe_main[i], kobe_main[i+1]) for i in range(len(kobe_main)-1)]

# ---- 2. 宝塚本線 ----
takarazuka_main = [
    "大阪梅田", "中津", "十三", "三国", "庄内", "服部天神", "曽根", "岡町",
    "豊中", "蛍池", "石橋阪大前", "池田", "川西能勢口",
    "雲雀丘花屋敷", "山本", "中山観音", "売布神社", "清荒神", "宝塚"
]
takarazuka_main_edges = [(takarazuka_main[i], takarazuka_main[i+1]) for i in range(len(takarazuka_main)-1)]

# ---- 3. 京都本線 ----
kyoto_main = [
    "大阪梅田", "中津", "十三（京都線）", "南方", "崇禅寺", "淡路", "上新庄",
    "相川", "正雀", "摂津市", "南茨木", "茨木市", "総持寺", "富田",
    "高槻市", "上牧", "水無瀬", "大山崎", "長岡天神",
    "西山天王山", "桂",
    "西京極", "西院", "大宮", "烏丸", "京都河原町"
]
kyoto_main_edges = [(kyoto_main[i], kyoto_main[i+1]) for i in range(len(kyoto_main)-1)]

# ---- 4. 今津線 ----
imazu_line = [
    "宝塚", "宝塚南口", "逆瀬川", "小林", "仁川", "甲東園", "門戸厄神",
    "西宮北口", "阪神国道", "今津"
]
imazu_edges = [(imazu_line[i], imazu_line[i+1]) for i in range(len(imazu_line)-1)]

# ---- 5. 箕面線 ----
mino_line = [
    "石橋阪大前", "桜井", "牧落", "箕面"
]
mino_edges = [(mino_line[i], mino_line[i+1]) for i in range(len(mino_line)-1)]

# ---- 6. 千里線 ----
senri_line = [
    "天神橋筋六丁目", "柴島", "淡路", "下新庄", "吹田", "豊津",
    "江坂", "南千里", "千里山", "関大前", "北千里"
]
senri_edges = [(senri_line[i], senri_line[i+1]) for i in range(len(senri_line)-1)]

# ---- 7. 嵐山線 ----
arashiyama_line = [
    "桂", "上桂", "松尾大社", "嵐山"
]
arashiyama_edges = [(arashiyama_line[i], arashiyama_line[i+1]) for i in range(len(arashiyama_line)-1)]

# ---- 8. 伊丹線 ----
itami_line = [
    "塚口", "稲野", "新伊丹", "伊丹"
]
itami_edges = [(itami_line[i], itami_line[i+1]) for i in range(len(itami_line)-1)]

# ---- 9. 甲陽線 ----
koyo_line = [
    "西宮北口", "苦楽園口", "甲陽園"
]
koyo_edges = [(koyo_line[i], koyo_line[i+1]) for i in range(len(koyo_line)-1)]

# ============================================
# 全路線 STATIONS（重複除去済み）
# ============================================
STATIONS = list(set(
    kobe_main +
    takarazuka_main +
    kyoto_main +
    imazu_line +
    mino_line +
    senri_line +
    arashiyama_line +
    itami_line +
    koyo_line
))

# ============================================
# 全路線 EDGES（完全結合）
# ============================================
EDGES = (
    kobe_main_edges +
    takarazuka_main_edges +
    kyoto_main_edges +
    imazu_edges +
    mino_edges +
    senri_edges +
    arashiyama_edges +
    itami_edges +
    koyo_edges
)

# ============================================
# 1日券（阪急全線版）※神戸高速線を除く想定
# ============================================
HANKYU_ONE_DAY_PASS = 1300  # 円（プロト用の固定値）


# ============================================
# グラフ構築
# ============================================
def build_graph():
    graph = {s: [] for s in STATIONS}
    for a, b in EDGES:
        # 区間数1で双方向
        graph[a].append((b, 1))
        graph[b].append((a, 1))
    return graph


GRAPH = build_graph()


# ============================================
# ダイクストラ法（区間数最小の経路）
# ============================================
def dijkstra_sections(start, goal):
    if start not in GRAPH or goal not in GRAPH:
        return None, None

    queue = [(0, start, [])]  # (cost, station, path)
    visited = set()

    while queue:
        cost, station, path = heapq.heappop(queue)

        if station == goal:
            return cost, path + [station]

        if station in visited:
            continue

        visited.add(station)

        for next_station, weight in GRAPH[station]:
            heapq.heappush(queue, (cost + weight, next_station, path + [station]))

    return None, None


# ============================================
# 区間数 → 運賃（簡易モデル）
# ============================================
def calc_fare_by_sections(sections: int) -> int:
    """
    sections: 区間数（= 電車に乗る区間の数）

    本来の阪急は営業キロによる対キロ区間制だが、
    ここでは「区間数 ≒ 距離」とみなした簡易版の運賃モデル。
    必要に応じてチューニングしてOK。
    """
    if sections <= 0:
        return 0

    if sections <= 3:
        return 170
    elif sections <= 6:
        return 200
    elif sections <= 9:
        return 240
    elif sections <= 13:
        return 280
    elif sections <= 18:
        return 330
    elif sections <= 24:
        return 380
    elif sections <= 30:
        return 410
    elif sections <= 36:
        return 480
    else:
        return 540


# ============================================
# API エンドポイント
# ============================================


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/hankyu/stations", methods=["GET"])
def hankyu_stations():
    """
    利用可能な阪急の駅一覧を返す（UI用のプルダウンなどに利用）
    """
    return jsonify(sorted(STATIONS))


@app.route("/hankyu/route", methods=["GET"])
def hankyu_route():
    """
    クエリ:
      /hankyu/route?start=大阪梅田&goal=京都河原町

    レスポンス:
      - 経路（駅リスト）
      - 区間数
      - 想定運賃
      - 1日券の価格
      - どちらがお得かのメッセージ
    """
    start = request.args.get("start")
    goal = request.args.get("goal")

    if not start or not goal:
        return jsonify({"error": "start と goal を指定してください"}), 400

    sections, route = dijkstra_sections(start, goal)

    if route is None:
        return jsonify({"error": "経路が見つかりませんでした"}), 404

    fare = calc_fare_by_sections(sections)

    if fare >= HANKYU_ONE_DAY_PASS:
        recommendation = "阪急1日乗車券の方がお得な可能性が高いです"
    else:
        recommendation = "通常運賃の方が安いです（このルート想定では）"

    return jsonify({
        "start": start,
        "goal": goal,
        "route": route,
        "sections": sections,
        "estimated_fare": fare,
        "one_day_pass": HANKYU_ONE_DAY_PASS,
        "recommendation": recommendation,
    })


@app.route("/hankyu/multi", methods=["GET"])
def hankyu_multi_route():
    """
    例:
      /hankyu/multi?stops=大阪梅田,十三,西宮北口,甲陽園

    → 上記は
        大阪梅田 → 十三
        十三 → 西宮北口
        西宮北口 → 甲陽園
      の3区間を合計する。
    """

    stops_param = request.args.get("stops")

    if not stops_param:
        return jsonify({"error": "stops を指定してください（カンマ区切り）"}), 400

    stops = stops_param.split(",")

    if len(stops) < 2:
        return jsonify({"error": "最低2駅は必要です"}), 400

    total_sections = 0
    total_fare = 0
    all_routes = []

    # 区間ごとに計算
    for i in range(len(stops) - 1):
        start = stops[i]
        goal = stops[i + 1]

        sections, route = dijkstra_sections(start, goal)

        if route is None:
            return jsonify({
                "error": f"{start} → {goal} の経路が見つかりませんでした"
            }), 404

        fare = calc_fare_by_sections(sections)

        total_sections += sections
        total_fare += fare

        all_routes.append({
            "start": start,
            "goal": goal,
            "route": route,
            "sections": sections,
            "fare": fare
        })

    if total_fare >= HANKYU_ONE_DAY_PASS:
        recommendation = "阪急1日乗車券（1300円）の方がお得です"
    else:
        recommendation = "通常運賃合計の方が安いです"

    return jsonify({
        "stops": stops,
        "details": all_routes,
        "total_sections": total_sections,
        "total_fare": total_fare,
        "one_day_pass": HANKYU_ONE_DAY_PASS,
        "recommendation": recommendation
    })

@app.route("/hankyu/calc", methods=["GET"])
def hankyu_calc():
    """
    start: 出発駅
    goal: 最終到着駅
    stops: 途中下車する駅をカンマ区切りで指定（任意）

    例:
      /hankyu/calc?start=大阪梅田&goal=神戸三宮&stops=十三,西宮北口
    """

    start = request.args.get("start")
    goal = request.args.get("goal")
    stops_param = request.args.get("stops")

    if not start or not goal:
        return jsonify({"error": "start と goal は必須です"}), 400

    # 途中下車駅の処理
    if stops_param:
        stops = [s for s in stops_param.split(",") if s]
    else:
        stops = []

    # ==== 旅程のセット ====
    # start → （stops...） → goal の順に並べる
    journey = [start] + stops + [goal]

    # ==== 計算結果を入れる箱 ====
    all_routes = []
    total_sections = 0
    total_fare = 0

    # ==== 旅程を順番に計算 ====
    for i in range(len(journey) - 1):
        s = journey[i]
        g = journey[i + 1]

        sections, route = dijkstra_sections(s, g)

        if route is None:
            return jsonify({"error": f"{s} → {g} の経路が見つかりません"}), 404

        fare = calc_fare_by_sections(sections)

        total_sections += sections
        total_fare += fare

        all_routes.append({
            "start": s,
            "goal": g,
            "route": route,
            "sections": sections,
            "fare": fare
        })

    # ==== 1日券との比較 ====
    if total_fare >= HANKYU_ONE_DAY_PASS:
        recommendation = "阪急1日乗車券の方がお得です"
    else:
        recommendation = "通常運賃の方が安いです"

    return jsonify({
        "journey_order": journey,
        "details": all_routes,
        "total_sections": total_sections,
        "total_fare": total_fare,
        "one_day_pass": HANKYU_ONE_DAY_PASS,
        "recommendation": recommendation
    })

if __name__ == "__main__":
    # ローカルテスト用
    app.run(debug=True)

