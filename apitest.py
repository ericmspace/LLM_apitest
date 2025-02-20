from flask import Flask, jsonify
import openai
import requests
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import time
import threading
import anthropic
from concurrent.futures import ThreadPoolExecutor
import yaml

# 配置部分包括API的ID和模型
def load_api_configs(file_path='local.yaml'):
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

api_configs = load_api_configs() 
# mongodboDB配置
client = MongoClient('localhost', 27017)
db = client['llm_api_availability']
collection = db['api_status']

# Flask应用设置
app = Flask(__name__)
app.config['PORT'] = 9500

# 时区设置为东八区（UTC+8）
def get_east_8_timezone():
    return timezone(timedelta(hours=8))

# 修改：更新 save_to_mongo 函数，新增 req_ttft 字段
def save_to_mongo(client_id, model_name, result, response_time, speed, req_ttft):
    timestamp = datetime.now(get_east_8_timezone()).strftime("%Y-%m-%d %H:%M:%S")  # 强制使用东八区时间
    log_data = {
        "client_id": client_id,
        "model_name": model_name,
        "result": result,
        "speed": round(speed, 2) if speed > 0 else 0,
        "response_time": response_time,
        "req_ttft": req_ttft,  # 新增的流式请求首 token 时间指标
        "timestamp": timestamp
    }
    collection.insert_one(log_data)
    return log_data  # 返回保存的数据用于API响应

# 检查API可用性的函数，修改后包含流式请求测量 Req_TTFT
def check_api_status(api_config, api_type, model_name):
    client_id = api_config.get("id")  # 使用人工设置的id
    tokens_generated = 0
    req_ttft = 0  # 新增变量：请求到第一个 token 的时间
    msg = "Please使用以下模板创建一个自我介绍，不要加句号。name填入'迪力木拉提莫尔索'，age填入'18',hobby填入'打羽毛球、英语、法语、编程、旅游':'大家好，我的名字是{name},我来自美国洛杉矶，是一名华人，今年{age}岁，我平日里最大的爱好是{hobby}，我曾经前往新加坡、中国香港等多地旅游，希望在以后的日子里能够与各位和睦相处，我们是相亲相爱的一家人，大家有什么问题可以尽管来问我，我涉猎广泛，可以帮助大家尽一份心力，接下来我要背诵一篇诗文：侍卫之臣不懈于内，忠志之士忘身于外者，盖追先帝之殊遇，欲报之于陛下也。诚宜开张圣听，以光先帝遗德，恢弘志士之气，不宜妄自菲薄，引喻失义，以塞忠谏之路也。宫中府中，俱为一体，陟罚臧否，不宜异同。若有作奸犯科及为忠善者，宜付有司论其刑赏，以昭陛下平明之理，不宜偏私，使内外异法也。"
    try:
        # 针对OpenAI-compatible API执行双重请求
        if api_type in ["openai", "openrouter", "deepseek", "kimi", "volcengine", "Siflow", "azure", "Grok", "Qwen","GLM"]:
            # 检查无效的 API 密钥
            if api_config["api_key"] == "example":
                result = "unknown"
                adjusted_response_time = 999
                req_ttft = 999
                return result
            # 根据 api_type 创建对应的客户端并设置消息模板
            if api_type == "azure":
                print(f"正在检测的是: {api_type}的{model_name}模型")
                client_obj = openai.AzureOpenAI(
                    api_key=api_config["api_key"],
                    api_version="2024-02-01",
                    azure_endpoint=api_config["endpoint"],
                )
            else:
                print(f"正在检测的是: {api_type}的{model_name}模型")
                if "base_url" in api_config:
                    client_obj = openai.OpenAI(api_key=api_config['api_key'], base_url=api_config['base_url'])
                else:
                    client_obj = openai.OpenAI(api_key=api_config['api_key'])
            # 修改：执行流式请求以测量 Req_TTFT
            stream_start = time.time()
            stream_response = client_obj.chat.completions.create(model=model_name, messages=[{'role': 'user', 'content': msg}], stream=True)
            for chunk in stream_response:
                req_ttft = time.time() - stream_start
                # 只取第一个返回的 token/流式块时间
                break
            print(f"{model_name}的Req_TTFT: {req_ttft}")
            # 修改：执行非流式请求获取完整生成数据
            non_streaming_start = time.time()
            non_streaming_response = client_obj.chat.completions.create(model=model_name, messages=[{'role': 'user', 'content': msg}], stream=False)
            total_generation_time = time.time() - non_streaming_start
            # 修改：调整响应时间，减去流式请求的 Req_TTFT
            adjusted_response_time = total_generation_time - req_ttft if total_generation_time > req_ttft else total_generation_time
            tokens_generated = non_streaming_response.usage.completion_tokens if non_streaming_response.usage else 0
            print(f"{model_name}的Total tokens: {tokens_generated}")
        elif api_type == "dreamily":
            print(f"正在检测的是: {api_type}的{model_name}模型")
            if api_config["api_key"] == "example":
                result = "unknown"
                adjusted_response_time = 999
                req_ttft = 0
                return result
            else:
                client_obj = openai.OpenAI(api_key=api_config['api_key'], base_url=api_config['base_url'])
            non_streaming_start = time.time()
            msg = "Please使用以下模板创建一个自我介绍，不要加句号。name填入'迪力木拉提莫尔索'，age填入'18',hobby填入'打羽毛球、英语、法语、编程、旅游':'大家好，我的名字是{name},我来自美国洛杉矶，是一名华人，今年{age}岁，我平日里最大的爱好是{hobby}，我曾经前往新加坡、中国香港等多地旅游，希望在以后的日子里能够与各位和睦相处，我们是相亲相爱的一家人，大家有什么问题可以尽管来问我，我涉猎广泛，可以帮助大家尽一份心力，谢谢。"
            response = client_obj.chat.completions.create(model=model_name, messages=[{'role': 'user', 'content': msg}], stream=False)
            response_time = time.time() - non_streaming_start
            tokens_generated = 96 #注意Dreamily的非流式请求BUG无法按照非流式一次性返回，所以Tokens需要高度可预期并计算Prompt_tokens代替的数值，Prompt维护修改时此处需同步修改
            streaming_response = client_obj.chat.completions.create(model=model_name, messages=[{'role': 'user', 'content':msg}], stream=True)
            stream_start = time.time()
            for chunk in streaming_response:
                req_ttft = time.time() - stream_start
                # 只取第一个返回的 token/流式块时间
                break
            print(f"{model_name}的Req_TTFT: {req_ttft}")
            adjusted_response_time = response_time - req_ttft
        elif api_type == "anthropic":
            print(f"正在检测的是: {api_type}的{model_name}模型")
            client_obj = anthropic.Anthropic(api_key=api_config['api_key'])
            stream_start = time.time()
            tokens_generated = 0
            req_ttft = 0
            stream_response = client_obj.messages.create(
                model=model_name,
                max_tokens=892,
                messages=[{
                    "role": "user",
                    "content": msg
                }],
                stream=True,
            )
            for chunk in stream_response:
                # 第一个流式块到达时记录 req_ttft
                if req_ttft == 0:
                    req_ttft = time.time() - stream_start
                # 判断是否为 MessageDeltaEvent，从中提取 output_tokens
                if hasattr(chunk, 'delta') and hasattr(chunk, 'usage'):
                    # 获取 output_tokens
                    usage = chunk.usage
                    tokens_generated = usage.output_tokens if usage else 0
            print(f"{model_name}的Total tokens: {tokens_generated}")
            total_generation_time = time.time() - stream_start
            adjusted_response_time = total_generation_time - req_ttft if total_generation_time > req_ttft else total_generation_time
        else:
            result = "unknown"
            adjusted_response_time = 202
            req_ttft = 0
            speed = 0
            print(f"在单轮检测中不可用: {api_type}的{model_name}模型")
            return result
        result = categorize_response_time(adjusted_response_time)
        speed = tokens_generated / adjusted_response_time if adjusted_response_time > 0 and tokens_generated > 0 else 0
    except Exception as e:
        adjusted_response_time = 404
        result = "unknown"
        speed = 0
        req_ttft = 0
        flag = 0
        print(f"检测失败: {api_type}的{model_name}模型，错误：{str(e)}")
    # 存入MongoDB
    save_to_mongo(client_id, model_name, result, adjusted_response_time, speed, req_ttft)
    return result

# 根据响应时间分类
def categorize_response_time(response_time):
    if response_time < 5:
        return "smooth"
    elif response_time <= 30:
        return "available"
    elif response_time <= 50:
        return "congestion"
    elif response_time <= 100:
        return "lagging"
    else:
        return "unknown"

# 执行单次检查的函数
def initial_check():
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        # 遍历API提供商和客户端配置
        for api_type, api_clients in api_configs['apis'].items():
            for client_name, api_config in api_clients.items():
                # 针对每个提供商的模型进行检查
                for model_name in api_config['models']:
                    futures.append(executor.submit(check_api_status, api_config, api_type, model_name))
        # 等待所有线程完成
        for future in futures:
            future.result()

# 定时任务函数：每隔一段时间检查一次
def periodic_check():
    while True:
        initial_check()  # 执行初始化检查
        time.sleep(60*30)  # 每30分钟运行一次

# 启动Flask服务，提供结果的接口
@app.route('/result')
def result():
    # 从MongoDB获取所有数据
    all_data = list(collection.find())
    for entry in all_data:
        entry['_id'] = str(entry['_id'])  # 转换 ObjectId 为字符串
    return jsonify(all_data)

@app.route('/')
def home():
    return jsonify({"message": "LLM API Availability Service Running on Port 9500"})

#——————————————————————————————————————————————————
# 新增函数：获取最近8小时的数据并计算可用率
def calculate_availability():
    current_time = datetime.now(get_east_8_timezone())
    eight_hours_ago = current_time - timedelta(hours=8)
    eight_hours_ago_str = eight_hours_ago.strftime("%Y-%m-%d %H:%M:%S")

    # 优化后的聚合管道，新增 latest_req_ttft 字段
    pipeline = [
        {"$match": {"timestamp": {"$gte": eight_hours_ago_str}}},
        {"$sort": {"timestamp": -1}},  # 按时间倒序排序
        {"$group": {
            "_id": {"client_id": "$client_id", "model_name": "$model_name"},
            "recent_results": {"$push": "$$ROOT"},
            "latest_speed": {"$first": "$speed"},  # 获取最新记录的 speed
            "latest_response_time": {"$first": "$response_time"},  # 最新的响应时间
            "latest_req_ttft": {"$first": "$req_ttft"}  # 获取最新记录的 req_ttft
        }},
        {"$project": {
            "recent_results": {"$slice": ["$recent_results", 15]},
            "latest_speed": 1,
            "latest_response_time": 1,
            "latest_req_ttft": 1
        }}
    ]

    grouped_data = collection.aggregate(pipeline)
    stats_collection = db['api_statistics']

    for group in grouped_data:
        client_id = group["_id"]["client_id"]
        model_name = group["_id"]["model_name"]
        results = [r["result"] for r in group["recent_results"]]

        # 可用率计算
        if not results or all(r == "unknown" for r in results):
            availability = "unknown"
        else:
            available_count = sum(1 for r in results if r in ["smooth", "available", "congestion"])
            availability = f"{(available_count / len(results)) * 100:.2f}%"

        # 获取最新性能指标，包括 req_ttft
        latest_speed = group.get("latest_speed", 0)
        latest_response = f"{group.get("latest_response_time", 0):.3f}"
        latest_req_ttft = group.get("latest_req_ttft", 0)

        # 保存到统计集合，同一 client_id 与 model_name 只有一条记录（更新最新数据）
        stats_data = {
            "client_id": client_id,
            "model_name": model_name,
            "availability": availability,
            "speed": latest_speed,
            "response": latest_response,
            "req_ttft": latest_req_ttft,  # 新增的 req_ttft 指标
            "last_updated": current_time.strftime("%Y-%m-%d %H:%M:%S")
        }

        stats_collection.update_one(
            {"client_id": client_id, "model_name": model_name},
            {"$set": stats_data},
            upsert=True
        )

# 定时任务：每50分钟计算一次
def periodic_availability_check():
    while True:
        calculate_availability()
        time.sleep(50 * 60)

@app.route('/sta')
def api_statistics():
    # 从MongoDB的api_statistics集合中获取所有数据
    stats_collection = db['api_statistics']
    all_statistics = list(stats_collection.find())
    # 将每条记录中的 ObjectId 转换为字符串，以便 JSON 序列化
    for entry in all_statistics:
        entry['_id'] = str(entry['_id'])
    return jsonify(all_statistics)

from flask import render_template

@app.route('/stats')
def show_stats():
    stats_collection = db['api_statistics']
    all_statistics = list(stats_collection.find())
    for entry in all_statistics:
        entry['_id'] = str(entry['_id'])  # 转换 ObjectId 为字符串
    return render_template('api_statistics.html', statistics=all_statistics)

@app.route('/refresh')
def refresh():
    # 启动任务，执行 initial_check 和 calculate_availability
    def run_tasks():
        # 这里确保 tasks 完成后再返回响应
        initial_check()  # 执行 initial_check
        calculate_availability()  # 执行 calculate_availability
    run_tasks()
    # 等待任务完成并返回成功响应
    return jsonify({"status": "success", "message": "Refreshing data"})

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=app.config['PORT'])
    initial_check()  # 启动后立即执行一次初始化检查
    calculate_availability()  # 启动后立即执行一次统计计算
    # 启动Flask应用
    app.run(host='0.0.0.0', port=app.config['PORT'])
    # 启动定时检查线程
    threading.Thread(target=periodic_check, daemon=True).start()
    # 启动定时任务线程
    threading.Thread(target=periodic_availability_check, daemon=True).start()