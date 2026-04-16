from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    # รับข้อมูล JSON จาก LINE
    data = request.json
    print(json.dumps(data, indent=4, ensure_ascii=False))
    
    # ตรวจสอบว่ามี events หรือไม่
    if 'events' in data:
        for event in data['events']:
            source = event.get('source', {})
            source_type = source.get('type')
            
            # ถ้าเป็นข้อความกลุ่ม ให้พริ้นท์ groupId ออกมา
            if source_type == 'group':
                group_id = source.get('groupId')
                print(f"✅ สำเร็จ! พบ Group ID: {group_id}")
                
            elif source_type == 'user':
                user_id = source.get('userId')
                print(f"ได้รับข้อความจาก User ID: {user_id}")

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    print("🚀 เริ่มใช้งาน Webhook Server สำหรับเก็บ Group ID")
    app.run(port=5000, debug=True)
