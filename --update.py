#!/usr/bin/env python3
"""
视频库更新脚本 - 生成唯一文件名版本
"""

import os
import json
import glob
import subprocess
import base64
import time
from datetime import datetime
from pathlib import Path

class VideoLibraryUpdater:
    def __init__(self, repo_path=".", page_size=10, token_file_path="/Users/syh/git_token.txt"):
        self.repo_path = Path(repo_path)
        self.videos_path = self.repo_path / "videos"
        self.thumbnails_path = self.repo_path / "thumbnails"
        self.page_size = page_size
        self.token_file_path = Path(token_file_path)
        
        # 生成唯一的JSON文件名（使用时间戳）
        self.timestamp = int(time.time())
        self.json_filename = f"videos_{self.timestamp}.json"
        self.json_path = self.repo_path / self.json_filename
        
        # 检查FFmpeg是否可用
        self.ffmpeg_available = self.check_ffmpeg()
        
        # 初始化时读取token
        self.github_token = self.read_github_token()
        
        self.thumbnails_path.mkdir(exist_ok=True)
    
    def generate_unique_url(self, filename, file_type="video"):
        """生成唯一URL - 使用时间戳文件名"""
        base_url = f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main"
        
        if file_type == "video":
            return f"{base_url}/videos/{filename}"
        else:
            return f"{base_url}/thumbnails/{filename}"
    
    def update_main_json(self):
        """更新主videos.json文件，指向最新的数据文件"""
        main_json_path = self.repo_path / "videos.json"
        
        main_data = {
            "latest": self.json_filename,
            "timestamp": self.timestamp,
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dataUrl": f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/{self.json_filename}",
            "message": "使用 latest 字段指向当前有效的数据文件"
        }
        
        with open(main_json_path, 'w', encoding='utf-8') as f:
            json.dump(main_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 更新主索引文件: videos.json -> {self.json_filename}")

    # 保留其他原有方法...
    def get_video_files(self):
        """获取所有视频文件（返回完整路径）"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI', '*.mkv', '*.MKV', '*.webm', '*.WEBM']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(str(self.videos_path / ext)))
        
        return [Path(f) for f in video_files]
    
    def setup_git_commands(self):
        """设置Git命令"""
        if self.github_token:
            push_url = f"https://yezhu9181:{self.github_token}@github.com/yezhu9181/my-video-host.git"
            self.git_commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", f"视频库更新 {self.timestamp} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                ["git", "push", push_url, "main"]
            ]
            print("✅ Git命令已配置")
        else:
            self.git_commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", f"视频库更新 {self.timestamp}"],
                ["git", "push", "origin", "main"]
            ]
            print("⚠️  Git命令已配置（使用默认认证）")
    
    def check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def read_github_token(self):
        """从文件读取GitHub Token"""
        try:
            if self.token_file_path.exists():
                with open(self.token_file_path, 'r', encoding='utf-8') as f:
                    token = f.read().strip()
                    return token if token else None
        except:
            return None

    def generate_video_data(self, video_files):
        """生成视频数据"""
        videos = []
        
        for i, video_file in enumerate(sorted(video_files), 1):
            video_filename = video_file.name
            print(f"📹 处理视频 {i}/{len(video_files)}: {video_filename}")
            
            # 简化的处理逻辑
            name_without_ext = Path(video_filename).stem
            title = self.generate_friendly_title(name_without_ext)
            description = self.generate_description(title)
            file_size = self.get_file_size(video_filename)
            
            # 获取视频信息
            if self.ffmpeg_available:
                duration, resolution = self.get_video_info(video_filename)
            else:
                duration = self.estimate_duration(video_filename)
                resolution = self.get_video_dimensions_from_filename(video_filename)
            
            # 生成缩略图
            if self.ffmpeg_available:
                thumbnail_filename = self.extract_video_thumbnail(video_filename)
            else:
                thumbnail_filename = self.create_svg_thumbnail(video_filename, file_size)
            
            video_url = self.generate_unique_url(video_filename, "video")
            thumbnail_url = self.generate_unique_url(thumbnail_filename, "thumbnail") if thumbnail_filename else ""
            
            video_data = {
                "id": i,
                "title": title,
                "filename": video_filename,
                "url": video_url,
                "description": description,
                "duration": duration,
                "size": f"{file_size} MB",
                "thumbnail": thumbnail_url,
                "codec": "H.264",
                "resolution": resolution,
                "createdAt": datetime.now().strftime("%Y-%m-%d"),
                "thumbnailType": "JPG" if thumbnail_filename.endswith('.jpg') else "SVG",
                "timestamp": self.timestamp
            }
            
            videos.append(video_data)
        
        return videos

    # 简化的其他方法...
    def get_file_size(self, filename):
        file_path = self.videos_path / filename
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 1)
        return 0

    def estimate_duration(self, filename):
        size_mb = self.get_file_size(filename)
        estimated_seconds = int(size_mb / 0.25)
        estimated_seconds = min(estimated_seconds, 3600)
        if estimated_seconds < 60:
            return f"0:{estimated_seconds:02d}"
        else:
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60
            return f"{minutes}:{seconds:02d}"

    def generate_friendly_title(self, filename):
        name = filename.replace('_', ' ').replace('-', ' ')
        name_mapping = {
            "intro": "产品介绍视频", "tutorial": "使用教程", "demo": "功能演示"
        }
        for key, value in name_mapping.items():
            if key in filename.lower():
                return value
        return name.title()

    def generate_description(self, title):
        descriptions = {
            "产品介绍视频": "全面介绍产品的功能特性和使用场景",
            "使用教程": "详细的使用方法和操作步骤说明",
            "功能演示": "核心功能的实际使用演示"
        }
        return descriptions.get(title, f"这是关于{title}的详细说明视频")

    def run_git_commands(self):
        """执行Git命令"""
        print("\n🚀 开始执行Git命令...")
        success_count = 0
        
        for command in self.git_commands:
            try:
                original_cwd = os.getcwd()
                os.chdir(self.repo_path)
                result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                os.chdir(original_cwd)
                
                if result.returncode == 0:
                    print(f"✅ {command} 执行成功")
                    success_count += 1
                else:
                    print(f"❌ {command} 执行失败")
            except Exception as e:
                print(f"❌ 执行命令时发生错误: {e}")
        
        return success_count == len(self.git_commands)

    def update_videos_json(self):
        """更新视频数据文件"""
        print("🎬 视频库更新脚本 - 唯一文件名版本")
        print("=" * 60)
        print(f"🆚 数据文件: {self.json_filename}")
        
        if not self.videos_path.exists():
            print(f"❌ 错误: videos文件夹不存在")
            return False
        
        video_files = self.get_video_files()
        if not video_files:
            print("❌ 错误: 没有找到视频文件")
            return False
        
        print(f"📁 找到 {len(video_files)} 个视频文件")
        
        # 设置Git命令
        self.setup_git_commands()
        
        videos = self.generate_video_data(video_files)
        
        # 创建JSON数据
        updated_data = {
            "videos": videos,
            "pagination": {
                "total": len(videos),
                "page": 1,
                "pageSize": self.page_size,
                "totalPages": 1,
                "hasNext": False,
                "hasPrev": False
            },
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timestamp": self.timestamp,
            "filename": self.json_filename
        }
        
        # 写入文件
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            # 更新主索引文件
            self.update_main_json()
            
            print(f"\n✅ 成功生成数据文件: {self.json_filename}")
            print(f"📊 统计信息: {len(videos)} 个视频")
            
            # 执行Git命令
            git_success = self.run_git_commands()
            
            if git_success:
                print(f"\n🎉 所有任务完成！")
                print(f"🌐 最新数据文件: {self.json_filename}")
                print(f"💡 CDN将立即加载新文件，无缓存问题")
            else:
                print(f"\n⚠️  数据文件已生成，但Git推送可能有问题")
            
            return True
            
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='更新视频库配置并自动Git提交')
    parser.add_argument('--page-size', type=int, default=10, help='每页显示的视频数量')
    parser.add_argument('--no-git', action='store_true', help='不执行Git命令')
    
    args = parser.parse_args()
    
    updater = VideoLibraryUpdater(page_size=args.page_size)
    
    if args.no_git:
        updater.git_commands = []
        print("⚠️  Git命令已禁用")
    
    success = updater.update_videos_json()
    
    if success:
        print("\n✅ 脚本执行完成")
    else:
        print("\n❌ 脚本执行失败")

if __name__ == "__main__":
    main()