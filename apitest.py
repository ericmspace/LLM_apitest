# -*- coding: utf-8 -*-
"""LLM API Availability Monitoring Service | LLM API可用性监控服务

This module provides a Flask-based service to monitor and evaluate the availability and performance
of various LLM APIs (e.g., OpenAI, Anthropic). It includes periodic checks, MongoDB storage,
real-time statistics, and a web interface for results visualization.

此模块提供一个基于Flask的服务，用于监控和评估各种LLM API（如OpenAI、Anthropic）的可用性和性能。
包括定期检查、MongoDB存储、实时统计和结果可视化的Web界面。

Key Features | 主要功能:
- Periodic API status checks with response time and token generation speed | 定期API状态检查，包括响应时间和令牌生成速度
- MongoDB integration for logging and statistics | MongoDB集成用于日志记录和统计
- Real-time updates via Flask-SocketIO | 通过Flask-SocketIO实现实时更新
- Web endpoints for raw data and aggregated statistics | 提供原始数据和聚合统计的Web端点
"""

from flask import Flask, jsonify, render_template
import openai
import requests
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import time
import threading
import anthropic
from concurrent.futures import ThreadPoolExecutor
import yaml
from flask_socketio import SocketIO, emit


def load_api_configs(file_path: str = 'local.yaml') -> dict:
    """Load API configuration from a YAML file | 从YAML文件加载API配置

    Args:
        file_path (str): Path to the YAML configuration file. Defaults to 'local.yaml' | YAML配置文件路径，默认值为'local.yaml'

    Returns:
        dict: Parsed API configuration data | 解析后的API配置数据
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


api_configs = load_api_configs()

# MongoDB setup | MongoDB配置
client = MongoClient('localhost', 27017)
db = client['llm_api_availability']
collection = db['api_status']

# Flask application setup | Flask应用配置
app = Flask(__name__)
app.config['PORT'] = 9500
socketio = SocketIO(app)


def get_east_8_timezone() -> timezone:
    """Return timezone object for UTC+8 (East 8) | 返回UTC+8（东八区）的时区对象

    Returns:
        timezone: Timezone object set to UTC+8 | 设置为UTC+8的时区对象
    """
    return timezone(timedelta(hours=8))


def save_to_mongo(client_id: str, model_name: str, result: str, response_time: float, speed: float, req_ttft: float) -> dict:
    """Save API check result to MongoDB with East 8 timezone timestamp | 将API检查结果保存到MongoDB，使用东八区时间戳

    Args:
        client_id (str): Unique identifier for the API client | API客户端的唯一标识符
        model_name (str): Name of the model being checked | 被检查的模型名称
        result (str): Status result (e.g., 'smooth', 'available') | 状态结果（例如 'smooth', 'available'）
        response_time (float): Total response time in seconds | 总响应时间（秒）
        speed (float): Token generation speed (tokens per second) | 令牌生成速度（每秒令牌数）
        req_ttft (float): Time to first token in seconds for streaming requests | 流式请求首个令牌时间（秒）

    Returns:
        dict: The saved log data | 保存的日志数据
    """
    timestamp = datetime.now(get_east_8_timezone()).strftime("%Y-%m-%d %H:%M:%S")
    log_data = {
        "client_id": client_id,
        "model_name": model_name,
        "result": result,
        "speed": round(speed, 2) if speed > 0 else 0,
        "response_time": response_time,
        "req_ttft": req_ttft,
        "timestamp": timestamp
    }
    collection.insert_one(log_data)
    return log_data


def check_api_status(api_config: dict, api_type: str, model_name: str) -> str:
    """Check the status of an API endpoint and log the result | 检查API端点状态并记录结果

    Args:
        api_config (dict): Configuration for the API client (e.g., api_key, base_url) | API客户端配置（例如api_key, base_url）
        api_type (str): Type of API (e.g., 'openai', 'anthropic') | API类型（例如 'openai', 'anthropic'）
        model_name (str): Model name to test | 要测试的模型名称

    Returns:
        str: Status category (e.g., 'smooth', 'unknown') | 状态类别（例如 'smooth', 'unknown'）
    """
    client_id = api_config.get("id")
    tokens_generated = 0
    req_ttft = 0
    msg = (
        "Please使用以下模板创建一个自我介绍，不要加句号。"
        "name填入'迪力木拉提莫尔索'，age填入'18',hobby填入'打羽毛球、英语、法语、编程、旅游':"
        "'大家好，我的名字是{name},我来自美国洛杉矶，是一名华人，今年{age}岁，"
        "我平日里最大的爱好是{hobby}，我曾经前往新加坡、中国香港等多地旅游，"
        "希望在以后的日子里能够与各位和睦相处，我们是相亲相爱的一家人，"
        "大家有什么问题可以尽管来问我，我涉猎广泛，可以帮助大家尽一份心力，"
        "接下来我要背诵一篇诗文：侍卫之臣不懈于内，忠志之士忘身于外者，"
        "盖追先帝之殊遇，欲报之于陛下也。诚宜开张圣听，以光先帝遗德，"
        "恢弘志士之气，不宜妄自菲薄，引喻失义，以塞忠谏之路也。宫中府中，"
        "俱为一体，陟罚臧否，不宜异同。'"
    )

    try:
        if api_type in ["openai", "openrouter", "deepseek", "kimi", "volcengine", "Siflow", "azure", "Grok", "Qwen", "GLM"]:
            if api_config["api_key"] == "example":
                result = "unknown"
                adjusted_response_time = 999
                req_ttft = 999
                return result

            if api_type == "azure":
                print(f"正在检测的是: {api_type}的{model_name}模型 | Checking: {api_type}'s {model_name} model")
                client_obj = openai.AzureOpenAI(
                    api_key=api_config["api_key"],
                    api_version="2024-02-01",
                    azure_endpoint=api_config["endpoint"],
                )
            else:
                print(f"正在检测的是: {api_type}的{model_name}模型 | Checking: {api_type}'s {model_name} model")
                client_obj = openai.OpenAI(
                    api_key=api_config['api_key'],
                    base_url=api_config.get('base_url', None)
                )

            # Streaming request to measure Req_TTFT | 流式请求以测量Req_TTFT
            stream_start = time.time()
            stream_response = client_obj.chat.completions.create(
                model=model_name,
                messages=[{'role': 'user', 'content': msg}],
                stream=True
            )
            for chunk in stream_response:
                req_ttft = time.time() - stream_start
                break
            print(f"{model_name}的Req_TTFT: {req_ttft}")

            # Non-streaming request for total generation time | 非流式请求获取总生成时间
            non_streaming_start = time.time()
            non_streaming_response = client_obj.chat.completions.create(
                model=model_name,
                messages=[{'role': 'user', 'content': msg}],
                stream=False
            )
            total_generation_time = time.time() - non_streaming_start
            adjusted_response_time = max(total_generation_time - req_ttft, total_generation_time)
            tokens_generated = non_streaming_response.usage.completion_tokens if non_streaming_response.usage else 0
            print(f"{model_name}的Total tokens: {tokens_generated}")

        elif api_type == "dreamily":
            print(f"正在检测的是: {api_type}的{model_name}模型 | Checking: {api_type}'s {model_name} model")
            if api_config["api_key"] == "example":
                result = "unknown"
                adjusted_response_time = 999
                req_ttft = 0
                return result
            client_obj = openai.OpenAI(api_key=api_config['api_key'], base_url=api_config['base_url'])
            non_streaming_start = time.time()
            msg = "Please使用以下模板创建一个自我介绍，不要加句号。name填入'迪力木拉提莫尔索'，age填入'18',hobby填入'打羽毛球、英语、法语、编程、旅游':'大家好，我的名字是{name},我来自美国洛杉矶，是一名华人，今年{age}岁，我平日里最大的爱好是{hobby}，我曾经前往新加坡、中国香港等多地旅游，希望在以后的日子里能够与各位和睦相处，我们是相亲相爱的一家人，大家有什么问题可以尽管来问我，我涉猎广泛，可以帮助大家尽一份心力，谢谢。"
            response = client_obj.chat.completions.create(
                model=model_name,
                messages=[{'role': 'user', 'content': msg}],
                stream=False
            )
            response_time = time.time() - non_streaming_start
            tokens_generated = 96  # Note: Dreamily non-streaming bug workaround | 注意：Dreamily的非流式请求BUG无法按照非流式一次性返回，所以Tokens需要高度可预期并计算Prompt_tokens代替的数值，Prompt维护修改时此处需同步修改
            streaming_response = client_obj.chat.completions.create(
                model=model_name,
                messages=[{'role': 'user', 'content': msg}],
                stream=True
            )
            stream_start = time.time()
            for chunk in streaming_response:
                req_ttft = time.time() - stream_start
                break
            print(f"{model_name}的Req_TTFT: {req_ttft}")
            adjusted_response_time = response_time - req_ttft

        elif api_type == "anthropic":
            print(f"正在检测的是: {api_type}的{model_name}模型 | Checking: {api_type}'s {model_name} model")
            client_obj = anthropic.Anthropic(api_key=api_config['api_key'])
            stream_start = time.time()
            tokens_generated = 0
            req_ttft = 0
            stream_response = client_obj.messages.create(
                model=model_name,
                max_tokens=892,
                messages=[{"role": "user", "content": msg}],
                stream=True,
            )
            for chunk in stream_response:
                if req_ttft == 0:
                    req_ttft = time.time() - stream_start
                if hasattr(chunk, 'delta') and hasattr(chunk, 'usage'):
                    usage = chunk.usage
                    tokens_generated = usage.output_tokens if usage else 0
            print(f"{model_name}的Total tokens: {tokens_generated}")
            total_generation_time = time.time() - stream_start
            adjusted_response_time = total_generation_time - req_ttft if total_generation_time > req_ttft else total_generation_time

        else:
            result = "unknown"
            adjusted_response_time = 0
            req_ttft = 0
            speed = 0
            print(f"在单轮检测中不可用: {api_type}的{model_name}模型 | Unavailable in single-round check: {api_type}'s {model_name}")
            return result

        result = categorize_response_time(adjusted_response_time)
        speed = tokens_generated / adjusted_response_time if adjusted_response_time > 0 and tokens_generated > 0 else 0

    except Exception as e:
        adjusted_response_time = 0
        result = "unknown"
        speed = 0
        req_ttft = 0
        print(f"检测失败: {api_type}的{model_name}模型，错误：{str(e)} | Check failed: {api_type}'s {model_name}, error: {str(e)}")

    save_to_mongo(client_id, model_name, result, adjusted_response_time, speed, req_ttft)
    return result


def categorize_response_time(response_time: float) -> str:
    """Categorize response time into status levels | 根据响应时间分类状态级别

    Args:
        response_time (float): Response time in seconds | 响应时间（秒）

    Returns:
        str: Status category (e.g., 'smooth', 'lagging') | 状态类别（例如 'smooth', 'lagging'）
    """
    if response_time < 8.5:
        return "smooth"
    elif response_time <= 35:
        return "available"
    elif response_time <= 50:
        return "congestion"
    elif response_time <= 120:
        return "lagging"
    else:
        return "unknown"


def initial_check() -> None:
    """Perform a single round of API status checks | 执行单轮API状态检查"""
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = []
        for api_type, api_clients in api_configs['apis'].items():
            for client_name, api_config in api_clients.items():
                for model_name in api_config['models']:
                    futures.append(executor.submit(check_api_status, api_config, api_type, model_name))
        for future in futures:
            future.result()


def periodic_check() -> None:
    """Run periodic API status checks every 10 minutes | 每10分钟运行一次定期API状态检查"""
    while True:
        initial_check()
        calculate_availability()
        time.sleep(60 * 10)


@app.route('/result')
def result() -> jsonify:
    """Return all logged API status data from MongoDB | 从MongoDB返回所有记录的API状态数据

    Returns:
        jsonify: JSON response containing all logged data | 包含所有记录数据的JSON响应
    """
    all_data = list(collection.find())
    for entry in all_data:
        entry['_id'] = str(entry['_id'])
    return jsonify(all_data)


@app.route('/')
def home() -> jsonify:
    """Home endpoint indicating service status | 主页端点指示服务状态

    Returns:
        jsonify: JSON response with service message | 包含服务消息的JSON响应
    """
    return jsonify({"message": "LLM API Availability Service Running on Port 9500"})


def calculate_availability() -> None:
    """Calculate API availability based on the last 8 hours of data | 根据过去8小时的数据计算API可用性"""
    current_time = datetime.now(get_east_8_timezone())
    eight_hours_ago = current_time - timedelta(hours=8)
    eight_hours_ago_str = eight_hours_ago.strftime("%Y-%m-%d %H:%M:%S")

    pipeline = [
        {"$match": {"timestamp": {"$gte": eight_hours_ago_str}}},
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": {"client_id": "$client_id", "model_name": "$model_name"},
            "recent_results": {"$push": "$$ROOT"},
            "latest_speed": {"$first": "$speed"},
            "latest_response_time": {"$first": "$response_time"},
            "latest_req_ttft": {"$first": "$req_ttft"},
            "latest_timestamp": {"$first": "$timestamp"}
        }},
        {"$project": {
            "recent_results": {"$slice": ["$recent_results", 15]},
            "latest_speed": 1,
            "latest_response_time": 1,
            "latest_req_ttft": 1,
            "latest_timestamp": 1
        }}
    ]

    grouped_data = collection.aggregate(pipeline)
    stats_collection = db['api_statistics']

    for group in grouped_data:
        client_id = group["_id"]["client_id"]
        model_name = group["_id"]["model_name"]
        results = [r["result"] for r in group["recent_results"]]

        if not results or all(r == "unknown" for r in results):
            availability = "unknown"
        else:
            available_count = sum(1 for r in results if r in ["smooth", "available", "congestion"])
            availability = f"{(available_count / len(results)) * 100:.2f}%"

        latest_speed = group.get("latest_speed", 0)
        latest_response = f"{group.get('latest_response_time', 0):.3f}"
        latest_req_ttft = group.get("latest_req_ttft", 0)
        latest_timestamp = group.get("latest_timestamp", current_time.strftime("%Y-%m-%d %H:%M:%S"))

        stats_data = {
            "client_id": client_id,
            "model_name": model_name,
            "availability": availability,
            "speed": latest_speed,
            "response": latest_response,
            "req_ttft": latest_req_ttft,
            "last_updated": latest_timestamp
        }

        stats_collection.update_one(
            {"client_id": client_id, "model_name": model_name},
            {"$set": stats_data},
            upsert=True
        )


def periodic_availability_check() -> None:
    """Run availability calculation every 15 minutes | 每15分钟运行一次可用性计算"""
    while True:
        calculate_availability()
        socketio.emit('refresh_stats', {'message': 'Data refreshed'})
        time.sleep(15 * 60)


@app.route('/sta')
def api_statistics() -> jsonify:
    """Return aggregated API statistics from MongoDB | 从MongoDB返回聚合的API统计数据

    Returns:
        jsonify: JSON response with statistics | 包含统计数据的JSON响应
    """
    stats_collection = db['api_statistics']
    all_statistics = list(stats_collection.find())
    for entry in all_statistics:
        entry['_id'] = str(entry['_id'])
    return jsonify(all_statistics)


@app.route('/stats')
def show_stats() -> str:
    """Render statistics page with API data | 渲染包含API数据的统计页面

    Returns:
        str: Rendered HTML template | 渲染的HTML模板
    """
    stats_collection = db['api_statistics']
    all_statistics = list(stats_collection.find())
    for entry in all_statistics:
        entry['_id'] = str(entry['_id'])
    return render_template('api_statistics.html', statistics=all_statistics)


@app.route('/kanban')
def show_kanban() -> str:
    """Render kanban page with raw API status data | 渲染包含原始API状态数据的看板页面

    Returns:
        str: Rendered HTML template | 渲染的HTML模板
    """
    all_data = list(collection.find())
    for entry in all_data:
        entry['_id'] = str(entry['_id'])
    return render_template('kanban.html', data=all_data)


@app.route('/refresh')
def refresh() -> jsonify:
    """Manually trigger data refresh | 手动触发数据刷新

    Returns:
        jsonify: JSON response indicating success | 表示成功的JSON响应
    """
    def run_tasks():
        initial_check()
        calculate_availability()
    run_tasks()
    return jsonify({"status": "success", "message": "Refreshing data"})


if __name__ == '__main__':
    # Start periodic check thread | 启动定期检查线程
    threading.Thread(target=periodic_check, daemon=True).start()
    # Start periodic availability calculation thread | 启动定期可用性计算线程
    threading.Thread(target=periodic_availability_check, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=app.config['PORT'])