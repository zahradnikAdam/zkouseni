import network
import socket
import time
from machine import Pin, ADC
import dht
 
# Wi-Fi připojení s timeoutem
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect("adamekkkx", "adamek189")
 
    timeout = 10  # čekat max 10 sekund
    while not wlan.isconnected() and timeout > 0:
        print("⏳ Připojuji se k Wi-Fi...")
        time.sleep(1)
        timeout -= 1
 
    if wlan.isconnected():
        print("✅ Připojeno:", wlan.ifconfig())
        return wlan.ifconfig()[0]
    else:
        print("❌ Nepodařilo se připojit k Wi-Fi.")
        return "0.0.0.0"  # Vrátí IP 0.0.0.0, pokud není připojeno
 
# Inicializace komponent
sensor = dht.DHT11(Pin(15))
moisture = ADC(Pin(26))
relay = Pin(16, Pin.OUT)
relay.off()
 
# HTML stránka
def web_page(temp, hum, soil, auto):
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: sans-serif; text-align: center; background: #f5f5f5; }}
        .box {{ background: white; border-radius: 8px; box-shadow: 0 0 10px #ccc; padding: 20px; margin: 20px auto; width: 90%; max-width: 400px; }}
        button {{ padding: 10px 20px; font-size: 16px; border: none; background: #4CAF50; color: white; border-radius: 5px; cursor: pointer; }}
        button:hover {{ background: #45a049; }}
    </style>
</head>
<body>
    <h1>🌿 Chytrý květináč</h1>
    <div class="box">
        🌡️ <strong>Teplota:</strong> {temp}°C<br>
        💧 <strong>Vlhkost vzduchu:</strong> {hum}%<br>
        🌱 <strong>Vlhkost půdy:</strong> {soil}<br>
        🤖 <strong>Automatické zalévání:</strong> {"ANO" if auto else "NE"}
    </div>
    <form action="/water" method="get">
        <button type="submit">💦 Zalít nyní</button>
    </form>
</body>
</html>"""
 
# Spuštění webserveru
ip = connect_wifi()
addr = socket.getaddrinfo(ip, 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
print("🌐 Server běží na http://", ip)
 
# Parametry
auto_watering = True
THRESHOLD = 30000  # Práh pro suchou půdu (0–65535)
 
# Hlavní smyčka
while True:
    try:
        cl, addr = s.accept()
        print("🔗 Připojeno od", addr)
        request = cl.recv(1024).decode()
        print("📩 Request:", request)
 
        # Čtení senzorů
        try:
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
        except Exception as e:
            temp = "N/A"
            hum = "N/A"
            print("❌ Chyba čtení DHT11:", e)
 
        soil = moisture.read_u16()
        print(f"📊 Půdní vlhkost: {soil}")
 
        # Spuštění zalévání na vyžádání
        if "/water" in request:
            print("💧 Ruční zalévání...")
            relay.on()
            time.sleep(2)
            relay.off()
 
        # Automatické zalévání
        if auto_watering and isinstance(soil, int) and soil < THRESHOLD:
            print("⚠️ Sucho! Zalévám automaticky.")
            relay.on()
            time.sleep(2)
            relay.off()
 
        # Odeslání odpovědi (HTML)
        response = web_page(temp, hum, soil, auto_watering)
        cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
        cl.send(response)
        cl.close()
 
    except Exception as e:
        print("💥 Chyba:", e)
 
 