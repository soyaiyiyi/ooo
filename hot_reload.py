import logging
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_function):
        self.restart_function = restart_function
        self.last_modified = time.time()
        self.process = None

    def on_modified(self, event):
        # 过滤非Python文件
        if not event.is_directory and event.src_path.endswith('.py'):
            current_time = time.time()
            # 为了避免多次触发，设置一个短暂的延迟
            if current_time - self.last_modified > 1:
                self.last_modified = current_time
                logging.info(f"检测到文件变更: {event.src_path}")
                self.restart_function()

class HotReloader:
    def __init__(self, main_file='main.py'):
        self.main_file = main_file
        self.process = None
    
    def start(self):
        # 监控src目录下的所有文件变化
        path = os.path.join(os.getcwd(), 'src')
        event_handler = CodeChangeHandler(self.restart_app)
        
        # 启动文件监控
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        
        try:
            # 首次启动应用
            self.restart_app()
            
            # 保持脚本运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            if self.process:
                self.process.terminate()
                
        observer.join()
    
    def restart_app(self):
        # 如果有正在运行的进程，先终止
        if self.process and self.process.poll() is None:
            logging.info("关闭当前进程...")
            self.process.terminate()
            self.process.wait()
        
        # 启动新进程
        logging.info("启动应用...")
        
        # 使用uv run命令启动应用
        self.process = subprocess.Popen(['uv', 'run', self.main_file])

if __name__ == "__main__":
    reloader = HotReloader()
    reloader.start()
