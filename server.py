#	pip install flask flask-socketio eventlet
#	pip install flask websockets asyncio

import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import json,base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

connected_devices = {}

@socketio.on('register')
def handle_register(data):
    try:
        # 如果接收到的是字串，先轉 dict
        if isinstance(data, str):
            data = json.loads(data)

        device_id = data.get('deviceId')
        if device_id:
            connected_devices[request.sid] = device_id
            print(f"✅ 已註冊 device ID：{device_id} (SID: {request.sid})")

            # 發送指令"startRecording"給剛註冊的裝置
            socketio.emit('command', {'command': "startRecording"}, room=request.sid)
            print(f"已發送指令 startRecording 給 {device_id}")

        else:
            print("register 中沒有 deviceId")
    except Exception as e:
        print(f"註冊 deviceId 錯誤：{e}")

# WebSocket 事件：連線
@socketio.on('connect')
def handle_connect():
    print(f"🔌 連線：{request.sid}")

# WebSocket 事件：斷線
@socketio.on('disconnect')
def handle_disconnect():
    device_id = connected_devices.pop(request.sid, None)
    print(f"Client disconnected: {device_id} (sid={request.sid})")
    


'''
debug 用: 手動從伺服器發送其他指令
# REST API: 傳送指令給指定裝置
@app.route("/send_command", methods=["POST"])
def send_command():
    data = request.get_json()
    print("REST /send_command 收到:", data)  # <-- 加這行看有沒有進來
    device_id = data.get("deviceId")
    command = data.get("command")
    if not device_id or not command:
        return jsonify({"status": "error", "message": "缺少 deviceId 或 command"}), 400

    # 找到對應 sid 的 client
    sid = None
    for k, v in connected_devices.items():
        if v == device_id:
            sid = k
            break
    if not sid:
        return jsonify({"status": "error", "message": "裝置未連線"}), 404

    socketio.emit('command', {'command': command}, room=sid) #發送指令的格式
    return jsonify({"status": "success", "message": f"已發送指令 {command} 給 {device_id}"}), 200
'''
    
'''
手動從伺服器發送指令格式
curl -v -X POST http://localhost:5000/send_command   -H "Content-Type: application/json"   -d '{"deviceId":"9b7683fd6b6e686a","command":"startRecording"}'

'''

'''
test: whether ngrok is working
@app.route("/ping")
def ping():
    print("ping 收到")
    return "pong"
'''
#透過 socket.io來接收音檔，格式是Base64 字串
@socketio.on('upload_audio')
def handle_upload_audio(data):
    device_id = data.get('deviceId', 'unknown')
    audio_base64 = data.get('audioData', '')
    audio_format = data.get('format', '3gp')

    if not audio_base64:
        print(f"來自 {device_id} 的錄音資料為空")
        return

    try:
        audio_bytes = base64.b64decode(audio_base64)
        #音檔會存在 Flask server 啟動時的當前工作目錄
        filename = f"received_audio_{device_id}.{audio_format}" 
        with open(filename, 'wb') as f:
            f.write(audio_bytes)

        print(f"✅ 已收到錄音檔，儲存為 {filename}")


    except Exception as e:
        print(f"處理錄音檔錯誤：{e}")
        

#透過 socket.io來接收資料，封包格式是一個 JSON 物件
@socketio.on('upload_sensor')
def handle_sensor_data(data):
    sid = request.sid
    if sid not in connected_devices:
        print("收到感測資料，但裝置尚未註冊 deviceId")
        return  # 或者你可以暫存資料、丟警告等
    device_id = connected_devices[sid]
    print(f"收到來自 {device_id} 的感測資料: {data}")


'''
原始:透過 HTTP POST (@app.route('/upload', methods=['POST'])) 來接收資料
# 上傳資料路由
@app.route('/upload', methods=['POST'])
def upload():
    data = request.get_json()
    if data:
        print("📦 收到資料：", data)
        return jsonify({"status": "success", "message": "資料已接收"}), 200
    else:
        return jsonify({"status": "error", "message": "未收到有效 JSON"}), 400
'''

if __name__ == "__main__":
    # 用 socketio 啟動
    print("伺服器啟動，等待連線...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)


