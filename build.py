#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import shutil
import platform
import subprocess
from pathlib import Path

def main():
    """构建应用为可执行文件"""
    print("开始构建抢单助手应用...")
    
    # 确定当前操作系统
    system = platform.system()
    print(f"当前操作系统: {system}")
    
    # 项目根目录
    root_dir = Path(__file__).parent.absolute()
    dist_dir = root_dir / "dist"
    
    # 清理之前的构建
    if dist_dir.exists():
        print("清理之前的构建...")
        shutil.rmtree(dist_dir)
    
    # 创建构建命令
    cmd = [
        "pyinstaller",
        "--name=抢单助手",
        "--windowed",  # 无控制台窗口
        "--onedir",    # 单目录模式
        "--clean",     # 清理临时文件
        "--noconfirm", # 不确认覆盖
        f"--distpath={dist_dir}",
        "--add-data=src/frontend:src/frontend",  # 添加前端资源
        "--add-data=resources:resources",        # 添加资源文件
    ]
    
    # 根据操作系统添加特定选项
    if system == "Darwin":  # macOS
        cmd.extend([
            "--icon=resources/icon.icns",
            "--osx-bundle-identifier=com.getorder.app"
        ])
    elif system == "Windows":
        cmd.extend([
            "--icon=resources/icon.ico",
            "--version-file=version.txt"
        ])
    
    # 添加主脚本
    cmd.append("main.py")
    
    # 执行构建命令
    print("执行PyInstaller构建...")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("构建完成!")
        
        # 输出构建结果路径
        if system == "Darwin":
            app_path = dist_dir / "抢单助手.app"
            print(f"应用已构建到: {app_path}")
        elif system == "Windows":
            app_path = dist_dir / "抢单助手"
            print(f"应用已构建到: {app_path}")
        else:
            app_path = dist_dir / "抢单助手"
            print(f"应用已构建到: {app_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
