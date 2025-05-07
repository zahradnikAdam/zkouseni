import network
import socket
import time
from machine import Pin, ADC
import dht

# Kalibrace půdního senzoru
SOIL_DRY = 50000   # hodnota senzoru pro suchou půdu
SOIL_WET = 20000   # hodnota senzoru pro mokrou půdu

# Wi-Fi připojení
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect("adamekkkx", "adamek189")
    timeout = 10
    while not wlan.isconnected() and timeout > 0:
        print("⏳ Připojuji se k Wi-Fi...")
        time.sleep(1)
        timeout -= 1
    if wlan.isconnected():
        print("✅ Připojeno:", wlan.ifconfig())
        return wlan.ifconfig()[0]
    else:
        print("❌ Nepodařilo se připojit k Wi-Fi.")
        return "0.0.0.0"

# Inicializace komponent
sensor = dht.DHT11(Pin(15))
moisture = ADC(Pin(26))
relay = Pin(16, Pin.OUT)
relay.off()

# HTML stránka ve funkci
def web_page(temp, hum, soil_percent, auto):
    return f"""<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Chytrý květináč</title>
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            background-color: #ffe6f0;
            color: #4a0033;
        }}
        .container {{
            max-width: 500px;
            margin: auto;
            padding: 20px;
            background: #fff0f5;
            border-radius: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            margin-top: 40px;
        }}
        h1 {{
            color: #d81b60;
        }}
        .info {{
            font-size: 18px;
            margin: 12px 0;
        }}
        .label {{
            font-weight: bold;
        }}
        .status {{
            margin-top: 25px;
        }}
        button {{
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            background-color: #ec407a;
            color: white;
            border-radius: 10px;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }}
        button:hover {{
            background-color: #c2185b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌷 Chytrý květináč</h1>
        <div class="info"><span class="label">🌞 Teplota:</span> {temp}°C</div>
        <div class="info"><span class="label">💦 Vlhkost vzduchu:</span> {hum}%</div>
        <div class="info"><span class="label">🌸 Vlhkost půdy:</span> {soil_percent}%</div>
        <div class="info"><span class="label">🧠 Automatické zalévání:</span> {"ANO" if auto else "NE"}</div>
        <div class="status">
            <form action="/water" method="get">
                <button type="submit">🚿 Zalít nyní</button>
            </form>
        </div>
    </div>
</body>
</html>"""

# Spuštění serveru
ip = connect_wifi()
addr = socket.getaddrinfo(ip, 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
print("🌐 Server běží na http://", ip)

# Parametry
auto_watering = True

# Hlavní smyčka
while True:
    try:
        cl, addr = s.accept()
        print("🔗 Připojeno od", addr)
        request = cl.recv(1024).decode()
        print("📩 Request:", request)

        # Měření teploty a vlhkosti
        try:
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
        except Exception as e:
            temp = "N/A"
            hum = "N/A"
            print("❌ Chyba čtení DHT11:", e)

        # Čtení půdní vlhkosti a převod na %
        soil_raw = moisture.read_u16()
        soil_percent = int((SOIL_DRY - soil_raw) * 100 / (SOIL_DRY - SOIL_WET))
        soil_percent = max(0, min(100, soil_percent))
        print(f"📊 Půdní vlhkost: {soil_raw} ({soil_percent}%)")

        # Ruční zalévání
        if "/water" in request:
            print("🚿 Ruční zalévání spuštěno...")
            relay.on()
            time.sleep(2)
            relay.off()

        # Automatické zalévání
        if auto_watering and soil_percent < 30:
            print("⚠️ Půda je suchá! Spouštím automatické zalévání.")
            relay.on()
            time.sleep(2)
            relay.off()

        # Odpověď klientovi
        response = web_page(temp, hum, soil_percent, auto_watering)
        cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
        cl.send(response)
        cl.close()

    except Exception as e:
        print("💥 Chyba:", e)
