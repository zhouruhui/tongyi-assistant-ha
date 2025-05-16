# 通义助手 (Tongyi Assistant)

基于阿里云通义千问大语言模型的 Home Assistant 语音助手集成。

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

> 本项目是对 [c1pher-cn/tongyi_assistant](https://github.com/c1pher-cn/tongyi_assistant) 的二次开发，添加了更多功能和优化。

## 功能特点

- 基于通义千问大语言模型，提供智能对话功能
- 支持智能家居设备控制（灯光、空调、传感器等）
- 可自定义提示词模板，优化对话体验
- 支持中文交互，适合国内用户使用

## 安装方法

### 方法一：HACS 安装

1. 在 HACS 中添加自定义存储库:
   - 打开 HACS → 右上角三个点 → 自定义存储库
   - 输入存储库地址: `https://github.com/zhouruhui/tongyi-assistant-ha`
   - 类别选择: `集成`
   - 点击添加

2. 在 HACS 集成页面中找到并安装 `Tongyi Assistant`

### 方法二：手动安装

1. 下载此仓库的内容
2. 将 `custom_components/tongyi_assistant` 文件夹复制到您的 Home Assistant 配置目录中的 `custom_components` 文件夹

## 配置步骤

### 1. 获取通义千问 API 密钥

1. 前往[阿里云 DashScope 灵积模型服务](https://help.aliyun.com/zh/dashscope/developer-reference/activate-dashscope-and-create-an-api-key)
2. 注册/登录账号并开通服务（目前有免费额度可用）
3. 创建并获取 API Key

### 2. 在 Home Assistant 中配置集成

1. 转到 Home Assistant 的集成页面: 配置 → 设备与服务 → 集成
2. 点击右下角的 "添加集成" 按钮
3. 搜索 "Tongyi Assistant" 并选择
4. 输入您之前获取的 API Key，完成配置

### 3. 设置语音助手

1. 转到 Home Assistant 中的语音助手页面: 配置 → 语音助手
2. 点击右下角的 "+" 添加一个新助手
3. 配置对话代理，选择 "Tongyi Assistant"
4. 保存配置

## 使用提示

- **提示词自定义**: 在集成的选项页面中可以自定义提示词模板，根据您的需求调整
- **区域设置**: 默认配置会向模型提供三个区域的设备信息('餐厅','书房','客厅')，您可以根据自己的家居布局修改
- **令牌控制**: 设备信息会占用令牌量，设备越多占用的令牌越多，默认上限配置为1000

## 已知问题

- 当前版本对上下文支持有限
- 某些复杂的智能家居控制指令可能需要多次尝试
- 模型的回复有时不完全符合预期格式

## 最近更新

- 修复了配置流中的弃用警告
- 优化了错误处理和日志记录
- 改进了JSON解析逻辑，提高了稳定性

## 贡献指南

欢迎通过 Issue 和 Pull Request 参与项目开发！

## 致谢

- 感谢 [c1pher-cn](https://github.com/c1pher-cn) 提供的原始项目
- 感谢阿里云提供的通义千问模型服务

## 许可证

本项目采用 GPL-3.0 许可证
