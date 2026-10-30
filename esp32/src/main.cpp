
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <U8g2lib.h>

// OLED: SDA = GPIO8, SCL = GPIO9
U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(
    U8G2_R0,
    U8X8_PIN_NONE
);

// 填入你原来使用的 Wi-Fi 信息
const char* WIFI_SSID = "";
const char* WIFI_PASSWORD = "";

// Windows 电脑的 FastAPI 地址
const char* API_URL =
    "http://192.168.93.55:8001/display-status";

// 在 OLED 上显示一条提示
void showMessage(const char* line1, const char* line2) {
    oled.clearBuffer();
    oled.setFont(u8g2_font_6x12_tf);

    oled.drawStr(0, 20, line1);
    oled.drawStr(0, 38, line2);

    oled.sendBuffer();
}

// 显示机器人状态
void showRobotStatus(
    const char* person,
    const char* robot,
    bool online,
    bool running,
    const char* direction,
    float x,
    float y
) {
    char line[32];

    oled.clearBuffer();
    oled.setFont(u8g2_font_5x8_tf);

    // 第 1 行：人员
    snprintf(line, sizeof(line), "Person: %.18s", person);
    oled.drawStr(0, 8, line);

    // 第 2 行：机器人
    snprintf(line, sizeof(line), "Robot: %.18s", robot);
    oled.drawStr(0, 18, line);

    // 第 3 行：在线状态
    snprintf(
        line, sizeof(line), "Online: %s",
        online ? "YES" : "NO"
    );
    oled.drawStr(0, 28, line);

    // 第 4 行：运行状态
    snprintf(
        line, sizeof(line), "Run: %s",
        running ? "YES" : "NO"
    );
    oled.drawStr(0, 38, line);

    // 第 5 行：运动方向
    snprintf(line, sizeof(line), "Dir: %.15s", direction);
    oled.drawStr(0, 48, line);

    // 第 6 行：机器人坐标
    snprintf(
        line, sizeof(line), "X:%.2f Y:%.2f",
        x, y
    );
    oled.drawStr(0, 60, line);

    oled.sendBuffer();
}

void connectWiFi() {
    Serial.println();
    Serial.println("正在连接 Wi-Fi...");

    showMessage("Connecting WiFi", "Please wait...");

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;

    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("Wi-Fi 连接成功！");
        Serial.print("ESP32 IP: ");
        Serial.println(WiFi.localIP());

        showMessage("WiFi connected", "Loading robot...");
        delay(500);
    } else {
        Serial.println("Wi-Fi 连接失败");
        showMessage("WiFi failed", "Check WiFi settings");
    }
}

void getRobotStatus() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Wi-Fi 已断开，尝试重新连接...");
        showMessage("WiFi disconnected", "Reconnecting...");
        WiFi.reconnect();
        return;
    }

    WiFiClient client;
    HTTPClient http;

    if (!http.begin(client, API_URL)) {
        Serial.println("HTTP 初始化失败");
        showMessage("HTTP init failed", "Check API address");
        return;
    }

    http.setTimeout(5000);

    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();

        Serial.println("\n收到 FastAPI 数据：");
        Serial.println(payload);

        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, payload);

        if (error) {
            Serial.print("JSON 解析失败：");
            Serial.println(error.c_str());

            showMessage("JSON parse failed", "Check API response");
            http.end();
            return;
        }

        const char* person = doc["person"] | "unknown";
        const char* robot = doc["robot"] | "none";
        const char* direction = doc["direction"] | "unknown";

        bool online = doc["online"] | false;
        bool running = doc["running"] | false;

        float x = 0.0f;
        float y = 0.0f;

        if (!doc["position"].isNull()) {
            x = doc["position"]["x"] | 0.0f;
            y = doc["position"]["y"] | 0.0f;
        }

        Serial.println("--- 解析后的状态 ---");
        Serial.printf("人员：%s\n", person);
        Serial.printf("机器人：%s\n", robot);
        Serial.printf("在线：%s\n", online ? "是" : "否");
        Serial.printf("运行中：%s\n", running ? "是" : "否");
        Serial.printf("方向：%s\n", direction);
        Serial.printf("坐标：x=%.3f, y=%.3f\n", x, y);

        showRobotStatus(
            person, robot, online, running,
            direction, x, y
        );
    } else {
        Serial.printf(
            "HTTP 请求失败，状态码：%d\n",
            httpCode
        );

        char errorLine[24];
        snprintf(
            errorLine, sizeof(errorLine),
            "HTTP error: %d", httpCode
        );

        showMessage("API request failed", errorLine);
    }

    http.end();
}

void setup() {
    Serial.begin(115200);
    delay(500);

    // 初始化 I2C：参数顺序为 SDA、SCL
    Wire.begin(8, 9);

    // 初始化 OLED
    oled.begin();
    oled.setContrast(255);

    showMessage("Robot Terminal", "Starting...");

    Serial.println("机器人状态显示终端启动");

    connectWiFi();
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
    }

    if (WiFi.status() == WL_CONNECTED) {
        getRobotStatus();
    }

    delay(2000);
}
