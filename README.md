
# LLM API Availability Service / LLM API 可用性服务

This project is designed to monitor the availability and performance of various LLM (Large Language Model) APIs, such as OpenAI, Anthropic, Azure, and others. The system periodically checks the status of APIs, calculates metrics like response time, throughput, and Req+TTFT (Request + Token Time to First Token), and stores the results in MongoDB. It also provides a web interface to display the latest statistics and data.

此项目旨在监控各种 LLM（大型语言模型）API 的可用性和性能，如 OpenAI、Anthropic、Azure 等。该系统定期检查 API 的状态，计算响应时间、吞吐量和 Req+TTFT（请求 + Token 到首个 Token 的时间）等指标，并将结果存储在 MongoDB 中。它还提供了一个 Web 界面来显示最新的统计数据和信息。

## Features / 功能

- API Availability Monitoring: Periodic checks of LLM API status with response time categorization.  
  API 可用性监控：定期检查 LLM API 状态，并根据响应时间进行分类。

- Database Logging: Logs API status, speed, and response time to MongoDB.  
  数据库记录：将 API 状态、速度和响应时间记录到 MongoDB。

- Web Interface: Flask-based web interface to view statistics, search for providers and models, and refresh data.  
  Web 界面：基于 Flask 的 Web 界面，用于查看统计数据、搜索提供商和模型、以及刷新数据。

- Real-time Updates: Data is periodically refreshed every 10 minutes, and API statistics are computed every 15 minutes.  
  实时更新：数据每 10 分钟定期刷新，API 统计数据每 15 分钟计算一次。

- Search and Sort: Search for providers or models, and sort the data based on different columns like availability, speed, etc.
  搜索与排序：可以搜索提供商或模型，并根据可用性、速度等不同列进行排序。
  
- Dark Mode Support: The web interface supports both light and dark modes for improved user experience across different environments.
  暗黑模式支持：Web 界面支持暗黑模式，以在不同环境下提供更好的用户体验。
  
- Highcharts Acknowledgment: This project utilizes Highcharts for chart visualization. Due to the use of Highcharts, this project is non-commercial and for educational purposes only.
  感谢 Highcharts：本项目使用 Highcharts 进行图表可视化。由于使用了 Highcharts，本项目不可商用，仅供学习和交流。
  
- Acknowledgment to ColorfulCloud Tech: This project was completed during the author's internship at ColorfulCloud Tech, which coincided with the author's final semester as an undergraduate at Shandong University of Science and Technology. All rights and authorship of the results belong to the author under the internship agreement, and it does not involve any commercial company interests. The author is grateful to the university for allowing the flexibility to complete this internship during this period.
  感谢彩云科技：本项目是在作者在彩云科技（ColorfulCloud Tech.）实习期间完成的。根据实习协议，成果的所有权和署名权归作者所有，且不涉及任何商业公司利益。恰逢作者本科在山东科技大学的最后一个学期，感谢学校在这一重要时期给予的充分实践自由。
  
## Requirements / 环境要求
- Python 3.x
- Flask
- MongoDB (local or remote instance)
- `openai` library
- `anthropic` library
- `requests` library
- `pymongo` library
- `yaml` library

## Setup / 设置

### 1. Install Dependencies / 安装依赖

First, install the necessary Python packages:

```bash
pip install Flask pymongo openai anthropic requests pyyaml
```

### 2. MongoDB Setup / MongoDB 设置

Make sure you have a running MongoDB instance. You can run MongoDB locally or use a remote service. Update the MongoDB connection in your code if needed.  
确保您有一个正在运行的 MongoDB 实例。您可以在本地运行 MongoDB 或使用远程服务。如果需要，请更新代码中的 MongoDB 连接。

### 3. API Configurations / API 配置

Create a `local.yaml` file in the same directory as the script, which contains your API configurations. Here's an example format:

创建一个 `local.yaml` 文件与脚本在同一目录下，文件包含您的 API 配置。下面是一个示例格式：

```yaml
apis:
  openai:
    openai_client:
      api_key: "your-api-key"
      models:
        - "gpt-3.5-turbo"
        - "gpt-4"
  azure:
    azure_client:
      api_key: "your-azure-api-key"
      endpoint: "your-azure-endpoint"
      models:
        - "gpt-3.5-turbo"
  anthropic:
    anthropic_client:
      api_key: "your-anthropic-api-key"
      models:
        - "claude-1"
```

### 4. Start the Application / 启动应用

Run the Flask application with the following command:

```bash
python app.py
```

This will start a web server at `http://localhost:9500` by default.  
这将默认启动一个 Web 服务器，地址为 `http://localhost:9500`。

### 5. Access the Web Interface / 访问 Web 界面

Once the Flask app is running, you can access the statistics and results by navigating to:

- Home: `http://localhost:9500/`  
  主页：`http://localhost:9500/`

- API Statistics: `http://localhost:9500/stats`  
  API 统计数据：`http://localhost:9500/stats`

- Record: `http://localhost:9500/result`  
  日志：`http://localhost:9500/result`
  
- Kanban: `http://localhost:9500/kanban`  
  看板：`http://localhost:9500/kanban`

You can also refresh the data by clicking the Refresh button in the web interface.  
您还可以通过点击 Web 界面中的 刷新 按钮来手动刷新数据。

## Functionality / 功能

### 1. Periodic Checks / 定期检查

The system performs periodic checks every 30 minutes to test API availability and stores the results in MongoDB.  
系统每 30 分钟执行一次定期检查，测试 API 的可用性，并将结果存储在 MongoDB 中。

### 2. API Response Time Categorization / API 响应时间分类

The response times of the APIs are categorized into the following groups:  
API 的响应时间被分类为以下几组：

- Smooth: Response time < 8.5 seconds  
  流畅：响应时间 < 8.5 秒

- Available: Response time ≤ 35 seconds  
  可用：响应时间 ≤ 35 秒

- Congestion: Response time ≤ 50 seconds  
  拥堵：响应时间 ≤ 50 秒

- Lagging: Response time ≤ 100 seconds  
  滞后：响应时间 ≤ 100 秒

- Unknown: Response time > 100 seconds or error occurred  
  未知：响应时间 > 100 秒或发生错误

### 3. Web Interface Features / Web 界面功能

- Search: You can search by provider and model name.  
  搜索：可以按提供商和模型名称进行搜索。

- Sorting: Click on column headers to sort the table by provider, model name, availability, speed, etc.  
  排序：点击列头进行排序，可以按提供商、模型名称、可用性、速度等排序。

- Refresh: Refresh the data manually by clicking the Refresh button. This will initiate an immediate API status check and data update.  
  刷新：通过点击 刷新 按钮手动刷新数据。此操作将立即启动 API 状态检查并更新数据。

## Database Structure / 数据库结构

### MongoDB Collections / MongoDB 集合

- api_status: Stores the results of API availability checks, including response times, speed, and Req+TTFT.  
  api_status：存储 API 可用性检查的结果，包括响应时间、速度和 Req+TTFT。

- api_statistics: Stores the latest aggregated statistics for each model and client, including availability and speed.  
  api_statistics：存储每个模型和客户端的最新汇总统计数据，包括可用性和速度。

## Customization / 自定义

- API Configuration: You can easily add new API providers and models by editing the `local.yaml` file.  
  API 配置：通过编辑 `local.yaml` 文件，您可以轻松添加新的 API 提供商和模型。

- MongoDB: Modify the MongoDB connection settings in the script if you're using a remote MongoDB instance.  
  MongoDB：如果您使用的是远程 MongoDB 实例，请修改脚本中的 MongoDB 连接设置。

## Contributing / 贡献

Feel free to fork the repository and submit pull requests. For bug reports or feature requests, open an issue on the GitHub repository.  
欢迎您分叉此项目并提交 Pull Request。对于错误报告或功能请求，请在 GitHub 仓库中提出问题。

## License / 许可证

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.  
本项目遵循 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。
