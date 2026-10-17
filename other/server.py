# -*- coding: utf-8 -*-
"""
一生一芯宣讲会 - 本地签到抽奖服务器
用法: python server.py
然后手机扫二维码访问 http://<电脑IP>:8000/
电脑打开 http://localhost:8000/lottery
"""
import http.server
import json
import os
import socket
import threading
import time
import urllib.parse

PORT = 8000
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signin_data.json")

# 奖品配置: (名称, 数量)
PRIZE_DEFS = [("雨伞", 1), ("帆布袋", 3), ("钥匙扣", 5), ("贴纸", 5)]

# 内存数据
names = []
winners = []
lock = threading.Lock()

def load_data():
    global names, winners
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                names = data.get("names", [])
                winners = data.get("winners", [])
        except:
            names = []
            winners = []

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"names": names, "winners": winners}, f, ensure_ascii=False, indent=2)

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


# ============ HTML 页面 ============

SIGNIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>一生一芯 · 签到</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #0d1117; color: #e6edf3; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 40px 20px; }
.header { text-align: center; margin-bottom: 40px; }
.header h1 { font-size: 22px; font-weight: 600; color: #e6edf3; }
.header p { font-size: 13px; color: #7d8590; margin-top: 8px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 32px 24px; width: 100%; max-width: 400px; }
.card h2 { font-size: 18px; margin-bottom: 20px; color: #3fb950; }
input { width: 100%; padding: 14px 16px; border-radius: 10px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-size: 16px; outline: none; margin-bottom: 16px; }
input:focus { border-color: #1f6feb; }
input::placeholder { color: #484f58; }
button { width: 100%; padding: 14px; border-radius: 10px; border: none; background: #238636; color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; }
button:active { background: #2ea043; }
button:disabled { background: #30363d; color: #7d8590; }
.success { text-align: center; padding: 40px 0; display: none; }
.success .check { width: 64px; height: 64px; background: #238636; border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; font-size: 36px; color: #fff; }
.success h2 { color: #3fb950; margin-bottom: 8px; }
.success p { color: #7d8590; font-size: 14px; }
.footer { margin-top: 40px; text-align: center; color: #484f58; font-size: 12px; }
</style>
</head>
<body>
<div class="header">
  <h1>一生一芯 · 校园宣讲会</h1>
  <p>计算机工程学院 · 现场签到</p>
</div>
<div class="card" id="formCard">
  <h2>填写你的姓名</h2>
  <input type="text" id="nameInput" placeholder="请输入真实姓名" maxlength="20" autocomplete="off">
  <button onclick="doSignIn()" id="submitBtn">确认签到</button>
</div>
<div class="success" id="successCard">
  <div class="check">&#10003;</div>
  <h2>签到成功！</h2>
  <p id="successText">欢迎你，请就座等待抽奖环节</p>
</div>
<div class="footer">计算机工程学院 · 一生一芯校园宣讲会</div>
<script>
document.getElementById("nameInput").addEventListener("keydown", function(e) { if (e.key === "Enter") doSignIn(); });
function doSignIn() {
  var name = document.getElementById("nameInput").value.trim();
  if (!name) { alert("请输入姓名"); return; }
  name = name.replace(/[<>&"]/g, "").replace(/\\s+/g, " ").substring(0, 20);
  var btn = document.getElementById("submitBtn");
  btn.disabled = true; btn.textContent = "提交中...";
  fetch("/api/signin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name })
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (data.ok) {
      document.getElementById("formCard").style.display = "none";
      document.getElementById("successCard").style.display = "block";
      document.getElementById("successText").textContent = data.message || ("欢迎你，" + name);
    } else {
      alert(data.message || "签到失败，请重试");
      btn.disabled = false; btn.textContent = "确认签到";
    }
  }).catch(function() {
    alert("网络错误，请重试");
    btn.disabled = false; btn.textContent = "确认签到";
  });
}
</script>
</body>
</html>"""


LOTTERY_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>一生一芯 · 现场抽奖</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #0d1117; color: #e6edf3; min-height: 100vh; overflow-x: hidden; }
.topbar { position: fixed; top: 0; left: 0; right: 0; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; background: rgba(13,17,23,0.9); z-index: 100; }
.topbar .count { font-size: 14px; color: #7d8590; }
.topbar .count b { color: #3fb950; }
.admin-btn { background: #21262d; border: 1px solid #30363d; color: #7d8590; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.admin-btn:hover { background: #30363d; color: #e6edf3; }
.title { text-align: center; padding: 80px 20px 20px; }
.title h1 { font-size: 28px; color: #3fb950; letter-spacing: 2px; }
.title p { font-size: 14px; color: #7d8590; margin-top: 8px; }
.stage { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 55vh; padding: 20px; }
.rolling-name { font-size: 72px; font-weight: 800; color: #e6edf3; text-shadow: 0 0 40px rgba(63,185,80,0.3); margin-bottom: 30px; min-height: 90px; display: flex; align-items: center; }
.draw-btn { width: 220px; height: 220px; border-radius: 50%; border: none; background: radial-gradient(circle at 30% 30%, #3fb950, #238636); color: #fff; font-size: 28px; font-weight: 700; cursor: pointer; box-shadow: 0 0 60px rgba(63,185,80,0.4); transition: transform 0.1s; }
.draw-btn:hover { transform: scale(1.05); }
.draw-btn:active { transform: scale(0.95); }
.draw-btn:disabled { background: #30363d; box-shadow: none; cursor: not-allowed; }
.prize-bar { display: flex; justify-content: center; gap: 24px; padding: 16px; flex-wrap: wrap; }
.prize-item { font-size: 14px; color: #7d8590; }
.prize-item b { color: #e6edf3; }
.history { max-width: 600px; margin: 20px auto; padding: 0 20px; }
.history h3 { font-size: 14px; color: #7d8590; margin-bottom: 10px; }
.history-item { padding: 8px 12px; background: #161b22; border-radius: 8px; margin-bottom: 6px; font-size: 14px; display: flex; justify-content: space-between; }
.history-item .prize { color: #d29922; }
.admin-panel { display: none; position: fixed; top: 50px; right: 20px; background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; z-index: 200; width: 280px; }
.admin-panel h3 { font-size: 15px; margin-bottom: 12px; color: #e6edf3; }
.admin-panel button { display: block; width: 100%; margin-bottom: 8px; padding: 10px; border-radius: 8px; border: 1px solid #30363d; background: #21262d; color: #e6edf3; cursor: pointer; font-size: 13px; }
.admin-panel button:hover { background: #30363d; }
.admin-panel button.danger { border-color: #da3633; color: #f85149; }
.name-list { max-height: 120px; overflow-y: auto; font-size: 12px; color: #484f58; margin-top: 8px; line-height: 1.6; }
</style>
</head>
<body>
<div class="topbar">
  <div class="count" id="countBar">已签到 <b>0</b> 人 · 已抽 <b>0</b> 人</div>
  <button class="admin-btn" onclick="toggleAdmin()">设置</button>
</div>

<div class="title">
  <h1>一生一芯 · 现场抽奖</h1>
  <p id="subtitle">等待同学签到...</p>
</div>

<div class="stage">
  <div class="rolling-name" id="displayName">等待签到...</div>
  <button class="draw-btn" id="drawBtn" onclick="startDraw()">抽奖</button>
</div>

<div class="prize-bar" id="prizeBar"></div>
<div class="history" id="history"></div>

<div class="admin-panel" id="adminPanel">
  <h3>管理</h3>
  <button onclick="refreshNow()">刷新名单</button>
  <button onclick="resetDraw()">只清开奖记录</button>
  <button class="danger" onclick="resetAll()">清空名单+重开</button>
  <div class="name-list" id="nameList"></div>
</div>

<script>
var winners = [];
var namePool = [];
var rolling = false;

function renderPrizes() {
  var prizes = { "雨伞": 1, "帆布袋": 3, "钥匙扣": 5, "贴纸": 5 };
  winners.forEach(function(w) { prizes[w.prize] = (prizes[w.prize] || 0) - 1; });
  var html = "";
  for (var p in prizes) {
    html += '<div class="prize-item">' + p + ' <b>' + Math.max(0, prizes[p]) + '</b></div>';
  }
  document.getElementById("prizeBar").innerHTML = html;
}

function renderHistory() {
  var h = document.getElementById("history");
  if (winners.length === 0) { h.innerHTML = ""; return; }
  var html = "<h3>中奖记录</h3>";
  winners.forEach(function(w) {
    html += '<div class="history-item"><span>' + w.name + '</span><span class="prize">' + w.prize + '</span></div>';
  });
  h.innerHTML = html;
}

function refreshNow() {
  fetch("/api/data").then(function(r) { return r.json(); }).then(function(data) {
    namePool = data.names || [];
    winners = data.winners || [];
    updateUI();
  });
}

function updateUI() {
  document.getElementById("countBar").innerHTML = "已签到 <b>" + namePool.length + "</b> 人 · 已抽 <b>" + winners.length + "</b> 人";
  var remaining = namePool.length - winners.length;
  document.getElementById("subtitle").textContent = remaining > 0 ? "剩余 " + remaining + " 人待抽" : "全部抽完";
  document.getElementById("drawBtn").disabled = (namePool.length - winners.length) <= 0 || rolling;
  renderPrizes();
  renderHistory();
  document.getElementById("nameList").textContent = namePool.join("、");
}

function toggleAdmin() {
  var p = document.getElementById("adminPanel");
  p.style.display = p.style.display === "block" ? "none" : "block";
}

function startDraw() {
  if (rolling) return;
  var available = namePool.filter(function(n) {
    return !winners.some(function(w) { return w.name === n; });
  });
  if (available.length === 0) { alert("没有可抽的人了"); return; }
  rolling = true;
  document.getElementById("drawBtn").disabled = true;
  var btn = document.getElementById("drawBtn");
  btn.textContent = "抽取中...";

  var duration = 2500;
  var start = Date.now();
  var timer = setInterval(function() {
    var n = available[Math.floor(Math.random() * available.length)];
    document.getElementById("displayName").textContent = n;
    if (Date.now() - start > duration) {
      clearInterval(timer);
      var winner = available[Math.floor(Math.random() * available.length)];
      document.getElementById("displayName").textContent = winner;
      finishDraw(winner);
    }
  }, 80);
}

function finishDraw(winnerName) {
  // Determine prize
  var prizes = { "雨伞": 1, "帆布袋": 3, "钥匙扣": 5, "贴纸": 5 };
  winners.forEach(function(w) { prizes[w.prize]--; });
  var availablePrizes = [];
  for (var p in prizes) {
    for (var i = 0; i < prizes[p]; i++) availablePrizes.push(p);
  }
  var prize = availablePrizes[Math.floor(Math.random() * availablePrizes.length)];

  winners.push({ name: winnerName, prize: prize });
  fetch("/api/winner", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: winnerName, prize: prize })
  });
  rolling = false;
  document.getElementById("drawBtn").textContent = "继续抽奖";
  updateUI();
}

function resetDraw() {
  if (!confirm("确定清空开奖记录？签到名单保留")) return;
  winners = [];
  fetch("/api/reset_winners", { method: "POST" });
  document.getElementById("displayName").textContent = "等待签到...";
  updateUI();
}

function resetAll() {
  if (!confirm("确定清空所有签到名单和开奖记录？")) return;
  names = [];
  winners = [];
  namePool = [];
  fetch("/api/reset_all", { method: "POST" });
  document.getElementById("displayName").textContent = "等待签到...";
  updateUI();
}

// Auto refresh
setInterval(refreshNow, 2000);
refreshNow();
</script>
</body>
</html>"""


# ============ HTTP Handler ============

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # quiet

    def _send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/" or path == "/signin":
            self._send_html(SIGNIN_HTML)
        elif path == "/lottery":
            self._send_html(LOTTERY_HTML)
        elif path == "/api/data":
            with lock:
                self._send_json({"names": names[:], "winners": winners[:]})
        else:
            self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(body)
        except:
            data = {}

        if path == "/api/signin":
            name = (data.get("name") or "").strip()
            name = name.replace("<", "").replace(">", "").replace('"', "").replace("&", "")
            name = " ".join(name.split())[:20]
            if not name:
                self._send_json({"ok": False, "message": "姓名不能为空"})
                return
            with lock:
                if name in names:
                    self._send_json({"ok": True, "message": name + "，你已签到过"})
                else:
                    names.append(name)
                    save_data()
                    self._send_json({"ok": True, "message": name + "，欢迎你"})
        elif path == "/api/winner":
            with lock:
                winners.append({"name": data.get("name", ""), "prize": data.get("prize", "")})
                save_data()
            self._send_json({"ok": True})
        elif path == "/api/reset_winners":
            with lock:
                winners.clear()
                save_data()
            self._send_json({"ok": True})
        elif path == "/api/reset_all":
            with lock:
                names.clear()
                winners.clear()
                save_data()
            self._send_json({"ok": True})
        else:
            self.send_error(404)


def main():
    load_data()
    ip = get_lan_ip()
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print("=" * 50)
    print("  一生一芯签到抽奖服务器已启动")
    print("=" * 50)
    print()
    print(f"  电脑端抽奖页:  http://localhost:{PORT}/lottery")
    print(f"  手机签到页:   http://{ip}:{PORT}/")
    print()
    print(f"  当前已签到 {len(names)} 人, 已抽 {len(winners)} 人")
    print()
    print("  按 Ctrl+C 停止")
    print("=" * 50)
    server.serve_forever()


if __name__ == "__main__":
    main()
