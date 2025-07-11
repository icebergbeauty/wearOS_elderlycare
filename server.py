import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import json,base64,os

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
            
            # 偵測跌倒
            fall = 1
            if fall == 1:
                print(f"🚨 偵測到跌倒！觸發處理流程 for {device_id}")
                fall_triggered(device_id)
		
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
    



# 🆕 專門處理跌倒事件觸發的函式
def fall_triggered(device_id):
    # 找出對應的 sid
    target_sid = None
    for sid, dev_id in connected_devices.items():
        if dev_id == device_id:
            target_sid = sid
            break

    if not target_sid:
        print(f"❌ 找不到 {device_id} 對應的 SID，無法發送命令")
        return

    # 傳送 fallcare.3gp 音檔
    audio_path = "fallcare.3gp"
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        socketio.emit('audio_message', {
            'format': '3gp',
            'audioData': audio_base64
        }, room=target_sid)

        print(f"📤 已發送音訊 fallcare.3gp 給 {device_id}")
    else:
        print("⚠️ 無法發送音訊：找不到 fallcare.3gp")
    
    # 發送指令 startRecording
    socketio.emit('command', {'command': "startRecording"}, room=target_sid)
    print(f"📡 已發送指令 startRecording 給 {device_id}")


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
    
    

if __name__ == "__main__":
    # 用 socketio 啟動
    print("伺服器啟動，等待連線...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)


