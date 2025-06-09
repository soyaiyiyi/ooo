# GetOrder Python GUI

这是一个使用Python实现的抢单GUI应用，基于原有的Electron项目重构而来。

## 特点

- 跨平台支持：同时支持Windows和macOS系统
- 内置Chromium浏览器：使用PyWebView提供内置浏览器功能
- 多线程抢单：使用Python多线程技术实现高效抢单流程
- 现代化UI：使用Web技术构建美观的用户界面

## 技术栈

- Python 3.8+
- PyWebView：提供内置Chromium浏览器支持
- Threading：实现多线程抢单功能
- Flask：作为后端API服务
- Vue.js：前端UI框架

## 安装

### 依赖项

```bash
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

## 开发

### 目录结构

- `src/` - 源代码目录
  - `backend/` - Python后端代码
  - `frontend/` - Web前端代码
- `resources/` - 资源文件
- `dist/` - 打包后的应用

### 构建

```bash
python build.py
```
